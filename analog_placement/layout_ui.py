import sys
import os
import time
import traceback

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QGroupBox, QFormLayout, QLineEdit, QLabel, QFileDialog,
    QTextEdit, QSpinBox, QDoubleSpinBox, QStackedWidget,
    QScrollArea, QFrame
)
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtCore import Qt, QThread, pyqtSignal

import matplotlib

matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

# 获取当前文件所在目录，用于临时切换工作目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 添加DGL_build目录到Python搜索路径
import sys

sys.path.append(os.path.join(BASE_DIR, "DGL_build"))

# 项目根目录，为了 import ui_style
sys.path.append(os.path.dirname(BASE_DIR))

# 页面样式和绘图字体助手都放在项目根的 ui_style.py，各功能页共用
from ui_style import PAGE_STYLE, cjk_font_properties

# 后台线程的存活引用。页面切换时 AutoLayoutWindow 会被销毁，
# 若 QThread 还挂在它下面会直接崩，所以放模块级集合里托管，线程跑完再移除。
_ACTIVE_WORKERS = set()



class LayoutWorker(QThread):
    """后台执行自动布局优化，避免十几秒的计算把界面卡死"""

    # 布局图数据：{kind, x, y, devices, sym_pairs, x_sym, title}
    figure_ready = pyqtSignal(object)
    succeeded = pyqtSignal(object, object)
    failed = pyqtSignal(str)

    def __init__(self, params, parent=None):
        super().__init__(parent)
        self.params = params

    def _on_plot(self, kind, x, y, devices, sym_pairs, x_sym, title):
        # 本方法运行在工作线程里，只允许发信号，
        # 不能碰任何 Qt 控件或 matplotlib canvas
        self.figure_ready.emit({
            "kind": kind,
            "x": x,
            "y": y,
            "devices": devices,
            "sym_pairs": sym_pairs,
            "x_sym": x_sym,
            "title": title,
        })

    def run(self):
        original_cwd = os.getcwd()
        try:
            os.chdir(BASE_DIR)

            # 导入布局函数
            from LAYOUT import optimize_layout

            x, y = optimize_layout(plot_callback=self._on_plot,
                                   plot_intermediate=False,
                                   **self.params)
            self.succeeded.emit(x, y)
        except Exception:
            self.failed.emit(traceback.format_exc())
        finally:
            os.chdir(original_cwd)


class AutoLayoutWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.start_time = 0.0
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet(PAGE_STYLE)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # 0号页：步骤3（主页面）  1号页：步骤1 + 步骤2
        # 页面内容比主窗口高，套一层滚动区，窗口小了也不会把控件裁掉
        self.stack = QStackedWidget()
        outer_layout.addWidget(self.stack)
        self.stack.addWidget(self.make_scrollable(self.build_main_page()))
        self.stack.addWidget(self.make_scrollable(self.build_preprocess_page()))
        self.stack.setCurrentIndex(0)

    @staticmethod
    def make_scrollable(inner):
        """把页面包进滚动区：空间够就撑满，不够就出滚动条"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(inner)
        return scroll

    # ==================== 主页面（步骤3 + 布局图 + 日志） ====================
    def build_main_page(self):
        page = QWidget()
        page.setObjectName("page")
        page_layout = QVBoxLayout(page)
        # 上下留白压紧，把高度让给布局图
        page_layout.setContentsMargins(14, 10, 14, 10)
        page_layout.setSpacing(9)

        # 顶部入口：进入网表处理（步骤1/2）
        top_bar = QHBoxLayout()
        self.preprocess_btn = QPushButton("网表处理 →")
        self.preprocess_btn.setObjectName("entryButton")
        self.preprocess_btn.setMinimumHeight(30)
        self.preprocess_btn.setCursor(Qt.PointingHandCursor)
        self.preprocess_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        top_bar.addWidget(self.preprocess_btn)
        top_bar.addStretch()
        page_layout.addLayout(top_bar)

        page_layout.addWidget(self.build_step3_group())
        page_layout.addWidget(self.build_figure_group(), 1)
        page_layout.addWidget(self.build_log_group())
        return page

    def build_step3_group(self):
        """步骤3：运行自动布局优化"""
        step3_group = QGroupBox("运行自动布局优化")
        step3_layout = QFormLayout(step3_group)
        step3_layout.setSpacing(6)
        step3_layout.setContentsMargins(9, 6, 9, 8)

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

        # 运行布局按钮：左右留弹簧，按内容宽度居中，不拉满整行
        self.layout_btn = QPushButton("开始自动布局优化")
        self.layout_btn.setObjectName("primaryButton")
        self.layout_btn.setMinimumHeight(34)
        self.layout_btn.setMinimumWidth(180)
        self.layout_btn.setCursor(Qt.PointingHandCursor)
        self.layout_btn.clicked.connect(self.run_layout)

        run_row = QHBoxLayout()
        run_row.addStretch()
        run_row.addWidget(self.layout_btn)
        run_row.addStretch()
        step3_layout.addRow(run_row)

        return step3_group

    def build_figure_group(self):
        """布局图：左右两幅内嵌画布，左边初始布局、右边最终布局"""
        figure_group = QGroupBox("布局图")
        figure_layout = QVBoxLayout(figure_group)
        figure_layout.setContentsMargins(6, 6, 6, 6)
        figure_layout.setSpacing(0)

        self.figure = Figure(figsize=(8, 3.6))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(300)
        figure_layout.addWidget(self.canvas)

        self.ax_initial = self.figure.add_subplot(1, 2, 1)
        self.ax_final = self.figure.add_subplot(1, 2, 2)
        self.reset_figure()
        return figure_group

    def build_log_group(self):
        """执行日志：高度压小，把空间让给布局图"""
        log_group = QGroupBox("执行日志")
        log_layout = QVBoxLayout(log_group)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(70)
        self.log_edit.setMaximumHeight(100)
        # 样式统一放在 PAGE_STYLE 里（控件自带的样式表会盖掉父级的，所以这里不单独设）
        log_layout.addWidget(self.log_edit)

        return log_group

    # ==================== 子页面（步骤1 + 步骤2） ====================
    def build_preprocess_page(self):
        page = QWidget()
        page.setObjectName("page")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(14, 10, 14, 10)
        page_layout.setSpacing(9)

        top_bar = QHBoxLayout()
        back_btn = QPushButton("← 返回")
        back_btn.setObjectName("entryButton")
        back_btn.setMinimumHeight(30)
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        top_bar.addWidget(back_btn)
        top_bar.addStretch()
        page_layout.addLayout(top_bar)

        page_layout.addWidget(self.build_step1_group())
        page_layout.addWidget(self.build_step2_group())
        page_layout.addStretch()
        return page

    def build_step1_group(self):
        """步骤1：CDL/SP网表转DGL图"""
        step1_group = QGroupBox("CDL/SP网表 → DGL图文件")
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

        return step1_group

    def build_step2_group(self):
        """步骤2：DGL图提取匹配约束"""
        step2_group = QGroupBox("DGL图 → 匹配约束文件(.sym)")
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

        return step2_group

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

    # ==================== 布局图绘制（只在GUI线程执行） ====================
    def reset_figure(self):
        """清空左右两幅图，各放一句提示"""
        self.draw_panel_placeholder(self.ax_initial, "初始布局")
        self.draw_panel_placeholder(self.ax_final, "最终布局")
        self.layout_figure()
        self.canvas.draw_idle()

    def draw_panel_placeholder(self, ax, title):
        ax.clear()
        ax.set_title(title, fontsize=11, color="#94a3b8",
                     fontproperties=cjk_font_properties())
        ax.text(0.5, 0.5, "等待运行…", ha="center", va="center", fontsize=10,
                color="#cbd5e0", fontproperties=cjk_font_properties())
        ax.set_axis_off()

    def draw_panel(self, ax, payload):
        """把一帧布局图画到指定的那一幅里"""
        # 懒导入：LAYOUT.visualization 会连带拉起 torch（约2秒），
        # 不放在模块顶层以免拖慢整个程序的启动
        from LAYOUT.visualization import draw_layout_on

        ax.clear()
        ax.set_axis_on()
        draw_layout_on(ax, payload["x"], payload["y"], payload["devices"],
                       payload["sym_pairs"], payload["x_sym"], payload["title"],
                       show_legend=False)
        self.layout_figure()
        self.canvas.draw_idle()

    def layout_figure(self):
        """两幅图共用一个图例，放到整张图下方，免得压住器件"""
        handles, labels = self.ax_initial.get_legend_handles_labels()
        if not handles:
            handles, labels = self.ax_final.get_legend_handles_labels()

        for legend in list(self.figure.legends):
            legend.remove()
        if handles:
            self.figure.legend(handles, labels, loc="lower center", ncol=3,
                               frameon=False, fontsize=9)

        self.figure.subplots_adjust(left=0.06, right=0.99, top=0.90,
                                    bottom=0.16 if handles else 0.06,
                                    wspace=0.16)

    def on_figure_ready(self, payload):
        """工作线程每画一张图就会发一次信号"""
        # 中间那张“第一阶段结束”的图不显示
        if payload["kind"] == "initial":
            self.draw_panel(self.ax_initial, payload)
        elif payload["kind"] == "final":
            self.draw_panel(self.ax_final, payload)

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
        """步骤3：运行自动布局（放到后台线程，界面不卡）"""
        netlist_path = self.layout_netlist_edit.text().strip()
        sym_path = self.sym_input_edit.text().strip()

        if not netlist_path or not os.path.exists(netlist_path):
            self.append_log("请选择有效的带约束网表文件", "error")
            return

        if not sym_path or not os.path.exists(sym_path):
            self.append_log("请选择有效的约束文件", "error")
            return

        if self.worker is not None and self.worker.isRunning():
            self.append_log("布局优化正在运行中，请等待完成", "warning")
            return

        # 获取所有UI参数
        params = dict(
            netlist_file=netlist_path,
            sym_file=sym_path,
            target_area=self.target_area_spin.value(),
            max_steps=self.max_steps_spin.value(),
            tmoc_weight=self.tmoc_weight_spin.value(),
            symmetry_weight=self.symmetry_weight_spin.value(),
            hpwl_weight=self.hpwl_weight_spin.value(),
            max_overlap_percent=self.max_overlap_spin.value(),
            max_symmetry_error=self.max_symmetry_error_spin.value(),
            max_oob_penalty=self.max_oob_penalty_spin.value(),
        )

        self.append_log("=" * 70)
        self.append_log("开始自动布局优化", "info")
        self.append_log(f"网表文件：{os.path.basename(netlist_path)}")
        self.append_log(f"约束文件：{os.path.basename(sym_path)}")
        self.append_log(f"目标面积：{params['target_area']} | 优化步数：{params['max_steps']}")
        self.append_log(f"共质心权重：{params['tmoc_weight']} | 对称性权重：{params['symmetry_weight']}")
        self.append_log("-" * 70)

        # 先把上一轮的图清掉，让初始图能立刻显示出来
        self.reset_figure()

        worker = LayoutWorker(params)
        self.worker = worker
        # 托管引用：页面被销毁时线程不会跟着被销毁
        _ACTIVE_WORKERS.add(worker)
        worker.finished.connect(lambda: _ACTIVE_WORKERS.discard(worker))

        worker.figure_ready.connect(self.on_figure_ready)
        worker.succeeded.connect(self.on_layout_succeeded)
        worker.failed.connect(self.on_layout_failed)
        worker.finished.connect(self.on_worker_finished)

        self.start_time = time.time()
        self.set_button_running(self.layout_btn, "正在进行自动布局优化...")
        worker.start()

    def on_layout_succeeded(self, x, y):
        elapsed = time.time() - self.start_time
        self.append_log(f"✅ 布局优化完成，总耗时 {elapsed:.2f} 秒", "success")
        self.append_log(f"器件X坐标：{x}")
        self.append_log(f"器件Y坐标：{y}")

    def on_layout_failed(self, error_text):
        elapsed = time.time() - self.start_time
        self.append_log(f"❌ 布局失败，耗时 {elapsed:.2f} 秒", "error")
        self.append_log(error_text, "error")

    def on_worker_finished(self):
        self.restore_button(self.layout_btn, "开始自动布局优化")
        self.append_log("=" * 70 + "\n")
        if self.worker is not None:
            self.worker.deleteLater()
            self.worker = None


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
