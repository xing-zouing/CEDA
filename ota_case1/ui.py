import sys
import os
import torch
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem,
    QMessageBox, QFileDialog, QTextEdit, QFormLayout, QGroupBox, QHeaderView
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QStandardItemModel, QStandardItem
from gymnasium import spaces
# ---------------- 全局配置 ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_ROOT = {
    "DDPG": os.path.join(BASE_DIR, "saved_weights"),
    "SAC": os.path.join(BASE_DIR, "saved_weights_sac")
}
OUTPUT_DIR = os.path.join(BASE_DIR, "output_circuit")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------- 关键修复：添加节点类型选择 ----------------
NODE_TYPE_MAP = {
    "GraphOTA": {"device": 11, "pin": 32},
    "GraphOTA2": {"device": 19, "pin": 32},
    "GraphOTA3": {"device": 20, "pin": 65}
}

# ---------------- 性能指标目标值配置 ----------------
PERFORMANCE_TARGETS = {
    "Gain (dB)": 60.0,
    "Bandwidth (Hz)": 1e6,
    "CMRR (dB)": 80.0,
    "PM (°)": 60.0,
    "Reward": 0.0
}


# ---------------- 工具函数：解析模型文件名 ----------------
def parse_model_filename(filename):
    result = {
        "valid": False,
        "is_actor": False,
        "ckt_name": "",
        "gnn_model": "",
        "reward": -999,
        "full_name": filename,
        "display_text": ""
    }
    if not filename.endswith(".pth"):
        return result
    parts = filename.split("_")
    if len(parts) < 5:
        return result
    if parts[0] != "Actor":
        return result
    result["is_actor"] = True
    result["ckt_name"] = parts[1]
    gnn_part = ""
    for part in parts:
        if part.startswith("ActorCritic"):
            gnn_part = part.replace("ActorCritic", "")
            break
    if not gnn_part:
        return result
    result["gnn_model"] = gnn_part
    reward_val = -999
    for part in parts:
        if part.startswith("reward="):
            try:
                reward_val = float(part.split("=")[1])
            except:
                pass
            break
    result["reward"] = reward_val
    result[
        "display_text"] = f"Reward: {reward_val:.2f} | Circuit: {result['ckt_name']} | Model: {result['gnn_model']} | File: {filename}"
    result["valid"] = True
    return result


# ---------------- 动态导入模块 ----------------
def get_ckt_graph_class(name, node_type="device"):
    from ckt_graphs import GraphOTA, GraphOTA2, GraphOTA3

    graph_map = {
        "GraphOTA": GraphOTA,
        "GraphOTA2": GraphOTA2,
        "GraphOTA3": GraphOTA3
    }

    # 直接传入node_type参数，让ckt_graphs自己初始化
    return lambda: graph_map[name](node_type=node_type)


def get_env_class(name):
    from ota import OTAEnv
    from ota1 import OTAEnv1
    env_map = {
        "OTAEnv (原版)": OTAEnv,
        "OTAEnv1 (加速版)": OTAEnv1
    }
    return env_map.get(name, OTAEnv)


def get_actor_model_class(name):
    from models import ActorCriticRGCN, ActorCriticGCN, ActorCriticGAT, ActorCriticMLP
    model_map = {
        "RGCN": ActorCriticRGCN,
        "GCN": ActorCriticGCN,
        "GAT": ActorCriticGAT,
        "MLP": ActorCriticMLP
    }
    return model_map.get(name, ActorCriticRGCN)


# ---------------- 后台线程：策略A - 确定性推理 ----------------
class OptimizeThread(QThread):
    update_log = pyqtSignal(str)
    update_result = pyqtSignal(dict)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self._is_running = True

    def stop(self):
        self._is_running = False
        self.update_log.emit("[INFO] 正在停止...")

    def run(self):
        try:
            self.update_log.emit("=" * 60)
            self.update_log.emit("[OK] 开始加载配置...")
            self.update_log.emit(f"   电路拓扑: {self.config['ckt_graph']}")
            self.update_log.emit(f"   节点类型: {self.config['node_type']}")
            self.update_log.emit(f"   Agent类型: {self.config['agent_type']}")
            self.update_log.emit(f"   GNN模型: {self.config['gnn_model']}")
            self.update_log.emit(f"   环境类型: {self.config['env_type']}")
            self.update_log.emit(f"   模型文件: {self.config['model_file']}")
            self.update_log.emit("=" * 60)

            # 1. 导入并初始化电路图类
            CktGraphClass = get_ckt_graph_class(self.config['ckt_graph'], self.config['node_type'])
            ckt_graph = CktGraphClass()

            # 2. 导入并初始化环境
            EnvClass = get_env_class(self.config['env_type'])
            env = EnvClass()

            env.CktGraph = ckt_graph
            env.num_nodes = ckt_graph.num_nodes
            env.obs_shape = ckt_graph.obs_shape
            env.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=env.obs_shape, dtype=np.float64)

            # 3. 导入并加载Actor模型
            ActorModelClass = get_actor_model_class(self.config['gnn_model'])
            actor = ActorModelClass.Actor(ckt_graph)


            model_path = os.path.join(WEIGHTS_ROOT[self.config['agent_type']], self.config['model_file'])
            self.update_log.emit(f"[INFO] 正在加载模型权重...")
            actor.load_state_dict(torch.load(model_path, weights_only=True, map_location=ckt_graph.device))
            actor.eval()

            # 4. 获取环境初始状态
            self.update_log.emit(f"[INFO] 正在初始化环境...")
            state, _ = env.reset()

            from utils import ActionNormalizer
            normalizer = ActionNormalizer(
                action_space_low=ckt_graph.action_space_low,
                action_space_high=ckt_graph.action_space_high
            )

            with torch.no_grad():
                if not self._is_running:
                    self.update_log.emit("[STOP] 优化已中断。")
                    return

                state_tensor = torch.FloatTensor(state).unsqueeze(0).to(ckt_graph.device)
                action_tensor = actor(state_tensor)
                action_tensor = action_tensor.clamp(-1, 1)

                # 反归一化回实际电路参数空间（用于UI展示）
                real_action = normalizer.action(action_tensor).flatten()
                # 对管子倍数M做取整处理
                for i in [2, 5, 8, 11]:
                    real_action[i] = int(np.clip(real_action[i], 1, 100))
                real_action = real_action.astype(float)

                self.update_log.emit("[INFO] 正在进行电路仿真...")
                # 传给env的是原始归一化值
                _, reward, _, _, info = env.step(action_tensor.flatten().cpu().numpy())

            self.update_log.emit("")
            self.update_log.emit(f"[SUCCESS] 推理完成！")
            self.update_log.emit(f"          Reward: {reward:.4f}")

            # 6. 整理结果参数名
            ckt_name = self.config['ckt_graph']
            LOCAL_PARAM_MAPPING = {
                "GraphOTA": [
                    "W_M0 (M0管宽度)", "L_M0 (M0管长度)", "M_M0 (M0管倍数)",
                    "W_M1 (M1/M2管宽度)", "L_M1 (M1/M2管长度)", "M_M1 (M1/M2管倍数)",
                    "W_M3 (M3/M4管宽度)", "L_M3 (M3/M4管长度)", "M_M3 (M3/M4管倍数)",
                    "W_M6 (M6管宽度)", "L_M6 (M6管长度)", "M_M6 (M6管倍数)",
                    "Vb (偏置电压)"
                ]
            }

            if ckt_name in LOCAL_PARAM_MAPPING and len(LOCAL_PARAM_MAPPING[ckt_name]) == len(real_action):
                param_names = LOCAL_PARAM_MAPPING[ckt_name]
            else:
                param_names = [f"电路参数_{i + 1}" for i in range(len(real_action))]

            params_dict = {name: float(val) for name, val in zip(param_names, real_action)}

            result = {
                "params": params_dict,
                "performance": {
                    "Gain": info.get("Gain", 0),
                    "Bandwidth": info.get("Bandwidth", 0),
                    "CMRR": info.get("CMRR", 0),
                    "PM": info.get("PM", 0),
                    "Reward": reward
                },
                "action": real_action,
                "config": self.config,
                "param_names": param_names,
                "info": info
            }

            self.update_result.emit(result)
            self.finished_signal.emit()

        except Exception as e:
            import traceback
            self.error_signal.emit(f"[ERROR] {str(e)}\n{traceback.format_exc()}")


# ---------------- 主窗口 ----------------
class CircuitOptWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.optimize_thread = None
        self.parsed_model_list = []
        self.has_valid_result = False
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        title = QLabel("模拟电路自动优化平台")
        title.setFont(QFont("WenQuanYi Micro Hei", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        self.init_config_tab()
        self.init_result_tab()

    def init_config_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        config_group = QGroupBox("核心配置")
        config_layout = QFormLayout(config_group)

        self.ckt_combo = QComboBox()
        self.ckt_combo.addItems(["GraphOTA", "GraphOTA2", "GraphOTA3"])
        self.ckt_combo.currentTextChanged.connect(self.refresh_model_list)
        config_layout.addRow("电路拓扑：", self.ckt_combo)

        self.node_type_combo = QComboBox()
        model = QStandardItemModel()
        device_item = QStandardItem("device级节点（器件级）")
        device_item.setData("device", Qt.UserRole)
        device_item.setEnabled(True)
        model.appendRow(device_item)
        pin_item = QStandardItem("pin级节点")
        pin_item.setData("pin", Qt.UserRole)
        pin_item.setEnabled(True)
        model.appendRow(pin_item)
        self.node_type_combo.setModel(model)
        self.node_type_combo.setCurrentIndex(0)
        self.node_type_combo.currentTextChanged.connect(self.refresh_model_list)
        config_layout.addRow("节点类型：", self.node_type_combo)

        self.agent_combo = QComboBox()
        self.agent_combo.addItems(["DDPG", "SAC"])
        self.agent_combo.currentTextChanged.connect(self.refresh_model_list)
        config_layout.addRow("Agent类型：", self.agent_combo)

        self.gnn_combo = QComboBox()
        self.gnn_combo.addItems(["RGCN", "GCN", "GAT", "MLP"])
        self.gnn_combo.currentTextChanged.connect(self.refresh_model_list)
        config_layout.addRow("GNN模型：", self.gnn_combo)

        self.env_combo = QComboBox()
        self.env_combo.addItems(["OTAEnv (原版)", "OTAEnv1 (加速版)"])
        config_layout.addRow("环境类型：", self.env_combo)

        layout.addWidget(config_group)

        model_group = QGroupBox("匹配的模型文件（仅Actor，按奖励从高到低排序）")
        model_layout = QVBoxLayout(model_group)

        self.model_combo = QComboBox()
        self.model_combo.setMinimumHeight(30)
        self.model_combo.setPlaceholderText("请先选择电路、Agent、GNN模型，自动匹配对应文件")
        model_layout.addWidget(QLabel("选择训练好的模型："))
        model_layout.addWidget(self.model_combo)

        refresh_btn = QPushButton("手动刷新模型列表")
        refresh_btn.clicked.connect(self.refresh_model_list)
        model_layout.addWidget(refresh_btn)

        layout.addWidget(model_group)

        self.optimize_btn = QPushButton("开始生成最优电路")
        self.optimize_btn.setFont(QFont("WenQuanYi Micro Hei", 14, QFont.Bold))
        self.optimize_btn.setMinimumHeight(50)
        self.optimize_btn.clicked.connect(self.start_optimize)
        layout.addWidget(self.optimize_btn)

        log_group = QGroupBox("优化日志")
        log_layout = QVBoxLayout(log_group)
        log_btn_layout = QHBoxLayout()
        log_label = QLabel("日志：")
        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.clicked.connect(self.clear_log)
        log_btn_layout.addWidget(log_label)
        log_btn_layout.addStretch()
        log_btn_layout.addWidget(clear_log_btn)
        log_layout.addLayout(log_btn_layout)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setPlaceholderText("优化日志会显示在这里...")
        log_layout.addWidget(self.log_edit)
        layout.addWidget(log_group)

        self.tab_widget.addTab(tab, "配置")
        self.refresh_model_list()

    def init_result_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        label = QLabel("最优电路设计结果")
        label.setFont(QFont("WenQuanYi Micro Hei", 16))
        layout.addWidget(label)

        split_layout = QHBoxLayout()

        # --- 电路参数表格 ---
        param_group = QGroupBox("电路参数")
        param_layout = QVBoxLayout(param_group)
        self.param_table = QTableWidget(13, 2)
        self.param_table.setHorizontalHeaderLabels(["参数名", "值"])

        header = self.param_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 第一列自适应内容
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # 第二列拉伸填充

        default_params = ["W0", "L0", "M0", "W1", "L1", "M1", "W3", "L3", "M3", "W6", "L6", "M6", "vb"]
        for i, p in enumerate(default_params):
            self.param_table.setItem(i, 0, QTableWidgetItem(p))
        param_layout.addWidget(self.param_table)
        split_layout.addWidget(param_group)

        # --- 性能指标表格 ---
        perf_group = QGroupBox("电路性能指标")
        perf_layout = QVBoxLayout(perf_group)

        self.perf_table = QTableWidget(5, 3)
        self.perf_table.setHorizontalHeaderLabels(["指标名", "当前值", "目标值"])

        # 设置性能表格列宽
        perf_header = self.perf_table.horizontalHeader()
        perf_header.setSectionResizeMode(QHeaderView.Stretch)

        perfs = ["Gain (dB)", "Bandwidth (Hz)", "CMRR (dB)", "PM (°)", "Reward"]
        for i, p in enumerate(perfs):
            self.perf_table.setItem(i, 0, QTableWidgetItem(p))
            target_val = PERFORMANCE_TARGETS.get(p, "-")
            # 格式化目标值显示
            if isinstance(target_val, float) and p == "Bandwidth (Hz)":
                target_str = f"{target_val:.0e}"
            elif isinstance(target_val, float):
                target_str = f"{target_val:.2f}"
            else:
                target_str = str(target_val)
            self.perf_table.setItem(i, 2, QTableWidgetItem(target_str))

        perf_layout.addWidget(self.perf_table)
        split_layout.addWidget(perf_group)

        layout.addLayout(split_layout)

        self.export_btn = QPushButton("SPICE NETLIST")
        self.export_btn.setMinimumHeight(40)
        self.export_btn.clicked.connect(self.export_spice)
        self.export_btn.setEnabled(False)
        layout.addWidget(self.export_btn)

        self.tab_widget.addTab(tab, "结果")

    def refresh_model_list(self):
        selected_ckt = self.ckt_combo.currentText()
        index = self.node_type_combo.currentIndex()
        selected_node_type = self.node_type_combo.itemData(index, Qt.UserRole)
        selected_agent = self.agent_combo.currentText()
        selected_gnn = self.gnn_combo.currentText()

        weights_dir = WEIGHTS_ROOT.get(selected_agent, "")
        self.model_combo.clear()
        self.parsed_model_list = []

        if not os.path.exists(weights_dir):
            self.model_combo.setPlaceholderText(f"目录不存在：{weights_dir}")
            return

        valid_files = []
        for filename in os.listdir(weights_dir):
            parsed = parse_model_filename(filename)
            if not parsed["valid"]:
                continue
            if parsed["ckt_name"] == selected_ckt and parsed["gnn_model"] == selected_gnn:
                valid_files.append(parsed)

        valid_files.sort(key=lambda x: x["reward"], reverse=True)
        self.parsed_model_list = valid_files

        if not valid_files:
            msg = f"未找到匹配的模型文件！\n\n电路：{selected_ckt}\n节点类型：{selected_node_type}\nGNN模型：{selected_gnn}\nAgent：{selected_agent}"
            QMessageBox.warning(self, "未找到模型", msg)
            self.model_combo.setPlaceholderText("未找到匹配的模型文件")
            return

        for parsed in valid_files:
            self.model_combo.addItem(parsed["display_text"], parsed["full_name"])

        self.log_edit.append(f"[OK] 刷新完成，找到 {len(valid_files)} 个匹配的模型文件")

    def start_optimize(self):
        if self.model_combo.count() == 0 or self.model_combo.currentData() is None:
            QMessageBox.warning(self, "警告", "没有可选择的有效模型文件！")
            return

        index = self.node_type_combo.currentIndex()
        selected_node_type = self.node_type_combo.itemData(index, Qt.UserRole)

        config = {
            "ckt_graph": self.ckt_combo.currentText(),
            "node_type": selected_node_type,
            "agent_type": self.agent_combo.currentText(),
            "gnn_model": self.gnn_combo.currentText(),
            "env_type": self.env_combo.currentText(),
            "model_file": self.model_combo.currentData()
        }

        self.log_edit.clear()

        self.optimize_thread = OptimizeThread(config)
        self.optimize_thread.update_log.connect(self.append_log)
        self.optimize_thread.update_result.connect(self.show_result)
        self.optimize_thread.error_signal.connect(self.show_error)
        self.optimize_thread.start()

        self.optimize_btn.setEnabled(False)
        self.optimize_btn.setText("正在优化中...")

    def append_log(self, text):
        self.log_edit.append(text)

    def clear_log(self):
        self.log_edit.clear()

    def show_result(self, result):
        params = result["params"]
        param_names = result["param_names"]
        self.param_table.setRowCount(len(param_names))
        for i, name in enumerate(param_names):
            self.param_table.setItem(i, 0, QTableWidgetItem(name))
            self.param_table.setItem(i, 1, QTableWidgetItem(f"{params[name]:.4f}"))


        self.param_table.resizeColumnsToContents()
        perf = result["performance"]
        perf_names = ["Gain (dB)", "Bandwidth (Hz)", "CMRR (dB)", "PM (°)", "Reward"]

        # 获取目标值用于比较
        thresholds = [
            PERFORMANCE_TARGETS["Gain (dB)"],
            PERFORMANCE_TARGETS["Bandwidth (Hz)"],
            PERFORMANCE_TARGETS["CMRR (dB)"],
            PERFORMANCE_TARGETS["PM (°)"],
            PERFORMANCE_TARGETS["Reward"]
        ]

        perf_values = [
            f"{perf['Gain']:.2f}",
            f"{perf['Bandwidth']:.2e}",
            f"{perf['CMRR']:.2f}",
            f"{perf['PM']:.2f}",
            f"{perf['Reward']:.2f}"
        ]

        for i, v in enumerate(perf_values):
            # 设置当前值
            item_val = QTableWidgetItem(v)

            # 颜色标记逻辑
            try:
                val = float(perf[perf_names[i].split(' ')[0]]) if i < 4 else float(perf['Reward'])
                if (i < 4 and val >= thresholds[i]) or (i == 4 and val >= 0):
                    item_val.setBackground(QColor(0, 255, 0, 50))
                else:
                    item_val.setBackground(QColor(255, 0, 0, 50))
            except:
                pass

            self.perf_table.setItem(i, 1, item_val)

        self.optimize_btn.setEnabled(True)
        self.optimize_btn.setText("开始生成最优电路")
        self.tab_widget.setCurrentIndex(1)
        self.has_valid_result = True
        self.export_btn.setEnabled(True)

    def show_error(self, error):
        QMessageBox.critical(self, "运行错误", error)
        self.optimize_btn.setEnabled(True)
        self.optimize_btn.setText("开始生成最优电路")

    def export_spice(self):
        if not self.has_valid_result:
            QMessageBox.warning(
                self,
                "无法导出",
                "请先点击「开始生成最优电路」，获得优化结果后再导出！"
            )
            return

        if self.param_table.rowCount() == 0 or self.param_table.item(0, 1) is None:
            QMessageBox.warning(self, "警告", "参数表格为空，请先运行优化！")
            return

        params = {}
        raw_value_list = []
        for i in range(self.param_table.rowCount()):
            name_item = self.param_table.item(i, 0)
            value_item = self.param_table.item(i, 1)
            if name_item and value_item:
                full_name = name_item.text()
                val = value_item.text()
                clean_key = full_name.split(' ')[0].split('(')[0]
                params[clean_key] = val
                raw_value_list.append(val)

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出SPICE网表",
            os.path.join(OUTPUT_DIR, "optimal_circuit.sp"),
            "SPICE Files (*.sp *.spice);;All Files (*.*)"
        )
        if not file_path:
            return

        config = self.ckt_combo.currentText()

        spice_header = f"""
* 最优电路设计 - 自动生成
* 配置：{config} | {self.agent_combo.currentText()} | {self.gnn_combo.currentText()}
* 参数列表：
"""
        for name, val in params.items():
            spice_header += f"* {name} = {val}\n"

        vb_val = "0.0"
        for possible_key in ['Vb', 'vb', 'Vb (偏置电压)', 'VBIAS2', 'VBIAS3']:
            if possible_key in params:
                vb_val = params[possible_key]
                break
        if len(raw_value_list) > 0:
            vb_val = raw_value_list[-1]

        spice_template = spice_header + f"""
* 电源定义
VDD VDD 0 1.8V
VSS VSS 0 0V
VB VB 0 {vb_val}V

* 仿真设置
.ac dec 10 1Hz 1GHz
.print ac vdb(OUT) vp(OUT)
.end
        """

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(spice_template)

        QMessageBox.information(self, "导出成功", f"SPICE网表已保存到：\n{file_path}")