import sys
import os
import time
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QGroupBox, QFormLayout, QLineEdit, QLabel, QFileDialog,
    QTextEdit, QSpinBox, QDoubleSpinBox
)
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtCore import Qt

# 获取当前文件所在目录，用于临时切换工作目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 添加DGL_build目录到Python搜索路径
import sys

sys.path.append(os.path.join(BASE_DIR, "DGL_build"))


class AutoLayoutWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # ==================== 步骤1：CDL/SP网表转DGL图 ====================
        step1_group = QGroupBox("步骤1：CDL/SP网表 → DGL图文件")
        step1_layout = QFormLayout(step1_group)
        step1_layout.setSpacing(10)

        # 输入网表文件
        self.cdl_input_edit = QLineEdit()
        self.cdl_input_edit.setPlaceholderText("选择CDL或SP格式的网表文件")
        cdl_browse_btn = QPushButton("浏览")
        cdl_browse_btn.clicked.connect(self.select_cdl_file)

        cdl_input_layout = QHBoxLayout()
        cdl_input_layout.addWidget(self.cdl_input_edit)
        cdl_input_layout.addWidget(cdl_browse_btn)
        step1_layout.addRow("输入网表：", cdl_input_layout)

        # 输出DGL文件
        self.dgl_output_edit = QLineEdit()
        self.dgl_output_edit.setPlaceholderText("选择DGL文件保存路径")
        dgl_browse_btn = QPushButton("浏览")
        dgl_browse_btn.clicked.connect(self.select_dgl_save_file)

        dgl_output_layout = QHBoxLayout()
        dgl_output_layout.addWidget(self.dgl_output_edit)
        dgl_output_layout.addWidget(dgl_browse_btn)
        step1_layout.addRow("输出DGL：", dgl_output_layout)

        # 转换按钮
        self.convert_btn = QPushButton("开始转换为DGL图")
        self.convert_btn.setMinimumHeight(35)
        self.convert_btn.clicked.connect(self.convert_to_dgl)
        step1_layout.addRow(self.convert_btn)

        main_layout.addWidget(step1_group)

        # ==================== 步骤2：DGL图提取匹配约束 ====================
        step2_group = QGroupBox("步骤2：DGL图 → 匹配约束文件(.sym)")
        step2_layout = QFormLayout(step2_group)
        step2_layout.setSpacing(10)

        # 输入DGL文件
        self.dgl_input_edit = QLineEdit()
        self.dgl_input_edit.setPlaceholderText("选择DGL图文件")
        dgl_input_browse_btn = QPushButton("浏览")
        dgl_input_browse_btn.clicked.connect(self.select_dgl_file)

        dgl_input_layout = QHBoxLayout()
        dgl_input_layout.addWidget(self.dgl_input_edit)
        dgl_input_layout.addWidget(dgl_input_browse_btn)
        step2_layout.addRow("输入DGL：", dgl_input_layout)

        # 输入原网表文件
        self.netlist_input_edit = QLineEdit()
        self.netlist_input_edit.setPlaceholderText("选择对应的原始网表文件")
        netlist_browse_btn = QPushButton("浏览")
        netlist_browse_btn.clicked.connect(self.select_netlist_file)

        netlist_input_layout = QHBoxLayout()
        netlist_input_layout.addWidget(self.netlist_input_edit)
        netlist_input_layout.addWidget(netlist_browse_btn)
        step2_layout.addRow("原始网表：", netlist_input_layout)

        # 提取约束按钮
        self.extract_btn = QPushButton("提取匹配约束并生成.sym文件")
        self.extract_btn.setMinimumHeight(35)
        self.extract_btn.clicked.connect(self.extract_constraint)
        step2_layout.addRow(self.extract_btn)

        main_layout.addWidget(step2_group)

        # ==================== 步骤3：运行自动布局优化 ====================
        step3_group = QGroupBox("步骤3：运行自动布局优化")
        step3_layout = QFormLayout(step3_group)
        step3_layout.setSpacing(10)

        # 输入带约束的网表
        self.layout_netlist_edit = QLineEdit()
        self.layout_netlist_edit.setPlaceholderText("选择带约束注释的网表文件")
        layout_netlist_browse_btn = QPushButton("浏览")
        layout_netlist_browse_btn.clicked.connect(self.select_layout_netlist)

        layout_netlist_layout = QHBoxLayout()
        layout_netlist_layout.addWidget(self.layout_netlist_edit)
        layout_netlist_layout.addWidget(layout_netlist_browse_btn)
        step3_layout.addRow("带约束网表：", layout_netlist_layout)

        # 输入约束文件
        self.sym_input_edit = QLineEdit()
        self.sym_input_edit.setPlaceholderText("选择.sym约束文件")
        sym_browse_btn = QPushButton("浏览")
        sym_browse_btn.clicked.connect(self.select_sym_file)

        sym_input_layout = QHBoxLayout()
        sym_input_layout.addWidget(self.sym_input_edit)
        sym_input_layout.addWidget(sym_browse_btn)
        step3_layout.addRow("约束文件(.sym)：", sym_input_layout)

        # ==================== 完整布局参数设置 ====================
        # 第一行参数
        param_row1 = QHBoxLayout()

        self.target_area_spin = QDoubleSpinBox()
        self.target_area_spin.setRange(1.0, 100.0)
        self.target_area_spin.setValue(10.0)
        self.target_area_spin.setSingleStep(1.0)
        param_row1.addWidget(QLabel("目标面积："))
        param_row1.addWidget(self.target_area_spin)

        self.max_steps_spin = QSpinBox()
        self.max_steps_spin.setRange(100, 10000)
        self.max_steps_spin.setValue(1000)
        self.max_steps_spin.setSingleStep(100)
        param_row1.addWidget(QLabel("优化步数："))
        param_row1.addWidget(self.max_steps_spin)

        step3_layout.addRow("基础参数：", param_row1)

        # 第二行参数
        param_row2 = QHBoxLayout()

        self.tmoc_weight_spin = QDoubleSpinBox()
        self.tmoc_weight_spin.setRange(0.0, 100.0)
        self.tmoc_weight_spin.setValue(20.0)
        self.tmoc_weight_spin.setSingleStep(5.0)
        param_row2.addWidget(QLabel("共质心权重："))
        param_row2.addWidget(self.tmoc_weight_spin)

        self.symmetry_weight_spin = QDoubleSpinBox()
        self.symmetry_weight_spin.setRange(0.0, 500.0)
        self.symmetry_weight_spin.setValue(100.0)
        self.symmetry_weight_spin.setSingleStep(10.0)
        param_row2.addWidget(QLabel("对称性权重："))
        param_row2.addWidget(self.symmetry_weight_spin)

        self.hpwl_weight_spin = QDoubleSpinBox()
        self.hpwl_weight_spin.setRange(0.0, 1.0)
        self.hpwl_weight_spin.setValue(0.01)
        self.hpwl_weight_spin.setSingleStep(0.01)
        param_row2.addWidget(QLabel("线长权重："))
        param_row2.addWidget(self.hpwl_weight_spin)

        step3_layout.addRow("优化权重：", param_row2)

        # 第三行参数
        param_row3 = QHBoxLayout()

        self.max_overlap_spin = QDoubleSpinBox()
        self.max_overlap_spin.setRange(0.0, 5.0)
        self.max_overlap_spin.setValue(2.0)
        self.max_overlap_spin.setSingleStep(0.1)
        param_row3.addWidget(QLabel("最大重叠率："))
        param_row3.addWidget(self.max_overlap_spin)

        self.max_symmetry_error_spin = QDoubleSpinBox()
        self.max_symmetry_error_spin.setRange(0.0, 1.0)
        self.max_symmetry_error_spin.setValue(0.1)
        self.max_symmetry_error_spin.setSingleStep(0.05)
        param_row3.addWidget(QLabel("最大对称误差："))
        param_row3.addWidget(self.max_symmetry_error_spin)

        self.max_oob_penalty_spin = QDoubleSpinBox()
        self.max_oob_penalty_spin.setRange(0.0, 1.0)
        self.max_oob_penalty_spin.setValue(0.1)
        self.max_oob_penalty_spin.setSingleStep(0.05)
        param_row3.addWidget(QLabel("越界惩罚系数："))
        param_row3.addWidget(self.max_oob_penalty_spin)

        step3_layout.addRow("约束参数：", param_row3)

        # 运行布局按钮
        self.layout_btn = QPushButton("开始自动布局优化")
        self.layout_btn.setMinimumHeight(40)
        self.layout_btn.setFont(QFont("WenQuanYi Micro Hei", 12, QFont.Bold))
        self.layout_btn.clicked.connect(self.run_layout)
        step3_layout.addRow(self.layout_btn)

        main_layout.addWidget(step3_group)

        # ==================== 日志输出区域 ====================
        log_group = QGroupBox("执行日志")
        log_layout = QVBoxLayout(log_group)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(220)
        self.log_edit.setPlaceholderText("执行日志会显示在这里...")
        self.log_edit.setStyleSheet("""
            QTextEdit {
                font-family: "WenQuanYi Micro Hei", monospace;
                font-size: 11px;
                line-height: 1.4;
            }
        """)
        log_layout.addWidget(self.log_edit)

        main_layout.addWidget(log_group)

    # ==================== 文件选择槽函数 ====================
    def select_cdl_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择网表文件", "", "网表文件 (*.cdl *.sp *.spice);;所有文件 (*.*)"
        )
        if file_path:
            self.cdl_input_edit.setText(file_path)
            # 自动填充输出DGL路径
            default_dgl = os.path.splitext(file_path)[0] + ".dgl"
            self.dgl_output_edit.setText(default_dgl)

    def select_dgl_save_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存DGL文件", "", "DGL文件 (*.dgl);;所有文件 (*.*)"
        )
        if file_path:
            self.dgl_output_edit.setText(file_path)

    def select_dgl_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择DGL文件", "", "DGL文件 (*.dgl);;所有文件 (*.*)"
        )
        if file_path:
            self.dgl_input_edit.setText(file_path)

    def select_netlist_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择原始网表文件", "", "网表文件 (*.cdl *.sp *.spice);;所有文件 (*.*)"
        )
        if file_path:
            self.netlist_input_edit.setText(file_path)

    def select_layout_netlist(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择带约束的网表文件", "", "网表文件 (*.cdl *.sp *.spice);;所有文件 (*.*)"
        )
        if file_path:
            self.layout_netlist_edit.setText(file_path)

    def select_sym_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择约束文件", "", "约束文件 (*.sym);;所有文件 (*.*)"
        )
        if file_path:
            self.sym_input_edit.setText(file_path)

    # ==================== 日志与状态管理 ====================
    def append_log(self, text, level="info"):
        """
        带级别和时间戳的日志输出
        level: info/success/warning/error
        """
        timestamp = time.strftime("%H:%M:%S", time.localtime())

        # 不同级别使用不同颜色
        color_map = {
            "info": "#1e293b",
            "success": "#16a34a",
            "warning": "#ca8a04",
            "error": "#dc2626"
        }

        color = color_map.get(level, "#1e293b")
        formatted_text = f'<span style="color: #64748b;">[{timestamp}]</span> <span style="color: {color};">{text}</span>'

        self.log_edit.append(formatted_text)
        # 自动滚动到底部
        self.log_edit.verticalScrollBar().setValue(
            self.log_edit.verticalScrollBar().maximum()
        )

    def set_button_running(self, button, running_text):
        """设置按钮为运行中状态"""
        button.setEnabled(False)
        button.setText(f"⏳ {running_text}")
        # 强制刷新UI
        button.repaint()

    def restore_button(self, button, original_text):
        """恢复按钮为正常状态"""
        button.setEnabled(True)
        button.setText(original_text)

    # ==================== 执行槽函数 ====================
    def convert_to_dgl(self):
        """步骤1：转换CDL/SP为DGL"""
        cdl_path = self.cdl_input_edit.text().strip()
        dgl_path = self.dgl_output_edit.text().strip()

        if not cdl_path or not os.path.exists(cdl_path):
            self.append_log("请选择有效的网表文件", "error")
            return

        # 设置按钮为运行中状态
        self.set_button_running(self.convert_btn, "正在转换DGL图...")

        self.append_log("=" * 70)
        self.append_log("开始转换网表为DGL图", "info")
        self.append_log(f"输入网表：{os.path.basename(cdl_path)}")
        self.append_log(f"输出路径：{os.path.basename(dgl_path)}")
        self.append_log("-" * 70)

        start_time = time.time()

        try:
            # 临时切换工作目录到analog-placement
            original_cwd = os.getcwd()
            os.chdir(BASE_DIR)

            # 导入转换函数
            from DGL_build.dgl_generator import cdl_to_dgl

            # 执行转换
            G_dgl, topCkt = cdl_to_dgl(cdl_path, dgl_path)

            elapsed = time.time() - start_time

            self.append_log(f"✅ DGL图转换完成，耗时 {elapsed:.2f} 秒", "success")
            self.append_log(f"节点数：{G_dgl.num_nodes()}")
            self.append_log(f"边数：{G_dgl.num_edges()}")
            self.append_log(f"节点特征维度：{G_dgl.ndata['feat'].shape}")

            # 自动填充步骤2的输入
            self.dgl_input_edit.setText(dgl_path)
            self.netlist_input_edit.setText(cdl_path)

        except Exception as e:
            elapsed = time.time() - start_time
            self.append_log(f"❌ 转换失败，耗时 {elapsed:.2f} 秒", "error")
            self.append_log(f"错误信息：{str(e)}", "error")
            import traceback
            self.append_log(traceback.format_exc(), "error")
        finally:
            os.chdir(original_cwd)
            # 恢复按钮状态
            self.restore_button(self.convert_btn, "开始转换为DGL图")
            self.append_log("=" * 70 + "\n")

    def extract_constraint(self):
        """步骤2：提取匹配约束"""
        dgl_path = self.dgl_input_edit.text().strip()
        netlist_path = self.netlist_input_edit.text().strip()

        if not dgl_path or not os.path.exists(dgl_path):
            self.append_log("请选择有效的DGL文件", "error")
            return

        if not netlist_path or not os.path.exists(netlist_path):
            self.append_log("请选择有效的原始网表文件", "error")
            return

        # 设置按钮为运行中状态
        self.set_button_running(self.extract_btn, "正在提取匹配约束...")

        self.append_log("=" * 70)
        self.append_log("开始提取匹配约束", "info")
        self.append_log(f"输入DGL：{os.path.basename(dgl_path)}")
        self.append_log(f"原始网表：{os.path.basename(netlist_path)}")
        self.append_log("-" * 70)

        start_time = time.time()

        try:
            # 临时切换工作目录到analog-placement
            original_cwd = os.getcwd()
            os.chdir(BASE_DIR)

            # 导入约束提取函数
            from DGL_build.extract import constraint_extraction

            # 执行提取
            output_netlist_path = constraint_extraction(dgl_path, netlist_path)

            elapsed = time.time() - start_time

            self.append_log(f"✅ 约束提取完成，耗时 {elapsed:.2f} 秒", "success")
            self.append_log(f"生成约束文件：{os.path.basename(os.path.splitext(netlist_path)[0] + '.sym')}")
            self.append_log(f"生成带约束网表：{os.path.basename(output_netlist_path)}")

            # 自动填充步骤3的输入
            self.layout_netlist_edit.setText(output_netlist_path)
            self.sym_input_edit.setText(os.path.splitext(netlist_path)[0] + '.sym')

        except Exception as e:
            elapsed = time.time() - start_time
            self.append_log(f"❌ 约束提取失败，耗时 {elapsed:.2f} 秒", "error")
            self.append_log(f"错误信息：{str(e)}", "error")
            import traceback
            self.append_log(traceback.format_exc(), "error")
        finally:
            os.chdir(original_cwd)
            # 恢复按钮状态
            self.restore_button(self.extract_btn, "提取匹配约束并生成.sym文件")
            self.append_log("=" * 70 + "\n")

    def run_layout(self):
        """步骤3：运行自动布局"""
        netlist_path = self.layout_netlist_edit.text().strip()
        sym_path = self.sym_input_edit.text().strip()

        # 获取所有UI参数
        target_area = self.target_area_spin.value()
        max_steps = self.max_steps_spin.value()
        tmoc_weight = self.tmoc_weight_spin.value()
        symmetry_weight = self.symmetry_weight_spin.value()
        hpwl_weight = self.hpwl_weight_spin.value()
        max_overlap_percent = self.max_overlap_spin.value()
        max_symmetry_error = self.max_symmetry_error_spin.value()
        max_oob_penalty = self.max_oob_penalty_spin.value()

        if not netlist_path or not os.path.exists(netlist_path):
            self.append_log("请选择有效的带约束网表文件", "error")
            return

        if not sym_path or not os.path.exists(sym_path):
            self.append_log("请选择有效的约束文件", "error")
            return

        # 设置按钮为运行中状态
        self.set_button_running(self.layout_btn, "正在进行自动布局优化...")

        self.append_log("=" * 70)
        self.append_log("开始自动布局优化", "info")
        self.append_log(f"网表文件：{os.path.basename(netlist_path)}")
        self.append_log(f"约束文件：{os.path.basename(sym_path)}")
        self.append_log(f"目标面积：{target_area} | 优化步数：{max_steps}")
        self.append_log(f"共质心权重：{tmoc_weight} | 对称性权重：{symmetry_weight}")
        self.append_log("-" * 70)

        start_time = time.time()

        try:
            # 临时切换工作目录到analog-placement
            original_cwd = os.getcwd()
            os.chdir(BASE_DIR)

            # 设置matplotlib后端避免冲突
            import matplotlib
            matplotlib.use('Qt5Agg')

            # 导入布局函数
            from LAYOUT import optimize_layout

            # 执行布局（传入所有参数）
            x, y = optimize_layout(
                netlist_file=netlist_path,
                sym_file=sym_path,
                target_area=target_area,
                max_steps=max_steps,
                tmoc_weight=tmoc_weight,
                symmetry_weight=symmetry_weight,
                hpwl_weight=hpwl_weight,
                max_overlap_percent=max_overlap_percent,
                max_symmetry_error=max_symmetry_error,
                max_oob_penalty=max_oob_penalty,
                plot_intermediate=True
            )

            elapsed = time.time() - start_time

            self.append_log(f"✅ 布局优化完成，总耗时 {elapsed:.2f} 秒", "success")
            self.append_log(f"器件X坐标：{x}")
            self.append_log(f"器件Y坐标：{y}")

        except Exception as e:
            elapsed = time.time() - start_time
            self.append_log(f"❌ 布局失败，耗时 {elapsed:.2f} 秒", "error")
            self.append_log(f"错误信息：{str(e)}", "error")
            import traceback
            self.append_log(traceback.format_exc(), "error")
        finally:
            os.chdir(original_cwd)
            # 恢复按钮状态
            self.restore_button(self.layout_btn, "开始自动布局优化")
            self.append_log("=" * 70 + "\n")


# 模块可以独立运行测试
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 设置全局字体
    font = QFont("WenQuanYi Micro Hei")
    font.setPointSize(12)
    app.setFont(font)

    window = AutoLayoutWindow()
    window.setWindowTitle("自动布局模块")
    window.resize(880, 1000)
    window.show()
    sys.exit(app.exec_())