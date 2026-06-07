import os
import sys
import warnings
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget,
    QVBoxLayout, QLabel
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ota_case1"))
# 过滤掉那个烦人的sip警告
warnings.filterwarnings("ignore", category=DeprecationWarning, message="sipPyTypeDict() is deprecated")

# 导入两个子模块
from device_generation.run import CircuitGenerator
from ota_case1.ui import CircuitOptWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("模拟电路设计与优化综合平台")
        self.resize(1600, 1000)  # 设置一个合适的窗口大小

        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)  # 去掉边距

        # 使用QTabWidget实现标签页切换
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)  # 标签在顶部
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #cccccc;
                top: -1px;
            }
            QTabBar::tab {
                padding: 10px 20px;
                font-size: 14px;
            }
            QTabBar::tab:selected {
                background-color: #3b82f6;
                color: white;
            }
        """)
        main_layout.addWidget(self.tab_widget)

        # 初始化已有页面
        self.circuit_generator_page = CircuitGenerator()
        self.circuit_optimizer_page = CircuitOptWindow()

        # 创建新的空页面
        self.layout_page = self.create_empty_page("布局功能", "自动布局功能正在开发中...")
        self.routing_page = self.create_empty_page("布线功能", "自动布线功能正在开发中...")

        # 添加所有标签页（按顺序排列）
        self.tab_widget.addTab(self.circuit_generator_page, "电路版图生成")
        self.tab_widget.addTab(self.circuit_optimizer_page, "电路参数优化")
        self.tab_widget.addTab(self.layout_page, "自动布局")
        self.tab_widget.addTab(self.routing_page, "自动布线")

    def create_empty_page(self, title, message):
        """创建一个统一风格的空页面"""
        page = QWidget()
        layout = QVBoxLayout(page)

        # 居中显示提示文字
        label = QLabel(message)
        label.setFont(QFont("WenQuanYi Micro Hei", 16))
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #666666;")

        layout.addWidget(label)
        return page


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 设置全局字体，解决Linux下中文显示问题
    font = QFont()
    font.setFamily("WenQuanYi Micro Hei")
    font.setPointSize(10)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())