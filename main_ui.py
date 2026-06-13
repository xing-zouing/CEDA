import os
import sys
import warnings
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget,
    QVBoxLayout, QLabel, QSizePolicy
)
from PyQt5.QtGui import QFont, QPalette, QColor
from PyQt5.QtCore import Qt

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ota_case1"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "analog_placement"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "rsmt_router"))
warnings.filterwarnings("ignore", category=DeprecationWarning, message="sipPyTypeDict() is deprecated")

from device_generation.run import CircuitGenerator
from ota_case1.ui import CircuitOptWindow
from analog_placement.layout_ui import AutoLayoutWindow
# 导入布局布线模块
from rsmt_router.routing_ui import RSMTRoutingWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("模拟电路设计与优化综合平台")
        self.resize(1000, 800)

        # 设置整体浅色背景
        self.setStyleSheet("QMainWindow { background-color: #f5f7fa; }")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)  # 增加外边距，留出呼吸空间

        # 创建标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)

        # ====================== 【新增修复1】标签自动平分宽度 + 禁止文字省略 ======================
        self.tab_widget.tabBar().setExpanding(True)  # 所有标签平分整个窗口宽度
        self.tab_widget.tabBar().setElideMode(Qt.ElideNone)  # 禁止文字省略，强制完整显示
        # ==========================================================================================

        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #ffffff;
                border-radius: 12px;
                margin-top: -1px;
            }
            QTabBar::tab {
                background: #e9edf2;
                color: #4a5568;
                /* ====================== 【修改修复2】调整内边距+增加最小宽度 ====================== */
                padding: 12px 16px;  /* 左右内边距从28px缩小，给文字留出更多空间 */
                min-width: 110px;    /* 每个标签最小宽度，保底放下6个汉字 */
                /* ================================================================================== */
                margin-right: 4px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                font-size: 15px;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #2b6ef7;
                font-weight: bold;
                border-bottom: 3px solid #2b6ef7;
            }
            QTabBar::tab:hover:!selected {
                background: #dce3eb;
                color: #1a202c;
            }
        """)
        main_layout.addWidget(self.tab_widget)

        # 初始化已有页面
        self.circuit_generator_page = CircuitGenerator()
        self.circuit_optimizer_page = CircuitOptWindow()

        # 创建开发中的功能页
        self.layout_page = AutoLayoutWindow()
        self.routing_page = RSMTRoutingWidget()

        # 添加标签页
        self.tab_widget.addTab(self.circuit_generator_page, "电路版图生成")
        self.tab_widget.addTab(self.circuit_optimizer_page, "电路参数优化")
        self.tab_widget.addTab(self.layout_page, "自动布局")
        self.tab_widget.addTab(self.routing_page, "自动布线")

    def create_empty_page(self, title, message):
        """创建一个带科技感图标和文字的占位页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)

        # 装饰图标（使用Unicode符号模拟）
        icon_label = QLabel("⚡")
        icon_label.setFont(QFont("WenQuanYi Micro Hei", 48))
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("color: #cbd5e0; margin-bottom: 20px;")

        # 提示文字
        text_label = QLabel(message)
        text_label.setFont(QFont("WenQuanYi Micro Hei", 16))
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setStyleSheet("color: #718096; background: transparent;")

        layout.addWidget(icon_label)
        layout.addWidget(text_label)
        return page


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 全局字体与调色板
    font = QFont()
    font.setFamily("WenQuanYi Micro Hei")
    font.setPointSize(10)
    app.setFont(font)

    # 设置全局默认调色板，确保所有控件继承浅色风格
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#f5f7fa"))
    palette.setColor(QPalette.WindowText, QColor("#1a202c"))
    palette.setColor(QPalette.Base, QColor("#ffffff"))
    palette.setColor(QPalette.AlternateBase, QColor("#f0f2f5"))
    palette.setColor(QPalette.ToolTipBase, QColor("#ffffff"))
    palette.setColor(QPalette.ToolTipText, QColor("#1a202c"))
    palette.setColor(QPalette.Text, QColor("#1a202c"))
    palette.setColor(QPalette.Button, QColor("#e9edf2"))
    palette.setColor(QPalette.ButtonText, QColor("#1a202c"))
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Highlight, QColor("#2b6ef7"))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())