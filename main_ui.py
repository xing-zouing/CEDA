import os
import sys
import warnings

if getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.join(sys._MEIPASS, 'site-packages'))


from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QPushButton,
    QFrame
)
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon, QPainter, QPixmap
from PyQt5.QtCore import Qt, pyqtSignal, QSize


if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

# 将子目录添加到 sys.path，保证 import 能找到模块
sys.path.append(os.path.join(base_path, "ota_case1"))
sys.path.append(os.path.join(base_path, "analog_placement"))
sys.path.append(os.path.join(base_path, "rsmt_router"))
from device_generation.run import CircuitGenerator
from ota_case1.ui import CircuitOptWindow
from analog_placement.layout_ui import AutoLayoutWindow
# 导入布局布线模块
from rsmt_router.routing_ui import RSMTRoutingWidget


# ====================== 功能页通用容器（带返回按钮） ======================
class FunctionPageWrapper(QWidget):
    """带顶部返回栏的功能页容器，包裹原有功能模块"""
    go_home_signal = pyqtSignal()  # 返回主页的信号

    def __init__(self, page_title, content_widget, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部导航栏
        top_bar = QWidget()
        top_bar.setFixedHeight(52)
        top_bar.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-bottom: 1px solid #e4e7ed;
            }
            QPushButton {
                background-color: #f5f7fa;
                border: 1px solid #dcdfe6;
                border-radius: 6px;
                padding: 6px 16px;
                color: #606266;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #ecf5ff;
                border-color: #2b6ef7;
                color: #2b6ef7;
            }
        """)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 0, 20, 0)

        back_btn = QPushButton("← 返回主页")
        back_btn.clicked.connect(self.go_home_signal.emit)

        title_label = QLabel(page_title)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1a202c;")
        title_label.setAlignment(Qt.AlignCenter)

        # 占位弹簧，让标题居中
        spacer = QWidget()
        spacer.setFixedWidth(80)

        top_layout.addWidget(back_btn)
        top_layout.addWidget(title_label, 1)
        top_layout.addWidget(spacer)

        main_layout.addWidget(top_bar)
        main_layout.addWidget(content_widget, 1)


# ====================== 主页（HomePage） ======================
class HomePage(QWidget):
    """软件主页，标题带右侧logo + 卡片式功能入口"""
    # 四个跳转信号，分别对应四个功能
    jump_to_gen = pyqtSignal()
    jump_to_opt = pyqtSignal()
    jump_to_place = pyqtSignal()
    jump_to_route = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("homePage")

        # 样式表：纯色背景 + 卡片按钮样式
        self.setStyleSheet("""
            #homePage {
                background-color: #f5f7fa;
            }
            #homePage QPushButton {
                background-color: #ffffff;
                border: 1px solid #e4e7ed;
                border-radius: 12px;
                font-size: 17px;
                font-weight: 500;
                color: #1a202c;
                padding: 40px 20px;
            }
            #homePage QPushButton:hover {
                background-color: #ffffff;
                border: 2px solid #2b6ef7;
                color: #2b6ef7;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setSpacing(60)
        main_layout.setContentsMargins(80, 80, 80, 80)

        # ===== 标题区域：parms大标题 + v0.6小字 + 右侧logo =====
        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title_layout.setSpacing(20)
        title_layout.setAlignment(Qt.AlignCenter)

        # 文字组合：parms + v0.6
        text_group = QWidget()
        text_layout = QHBoxLayout(text_group)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(6)
        text_layout.setAlignment(Qt.AlignBaseline)

        app_name = QLabel("parms")
        app_name.setStyleSheet("""
            font-size: 52px;
            font-weight: bold;
            color: #2b6ef7;
            letter-spacing: 2px;
        """)

        version_name = QLabel("v0.6")
        version_name.setStyleSheet("""
            font-size: 20px;
            font-weight: 500;
            color: #2b6ef7;
        """)

        text_layout.addWidget(app_name)
        text_layout.addWidget(version_name)

        # 右侧logo图片，高度与parms文字匹配
        logo_label = QLabel()
        logo_path = os.path.join(base_path, "assets", "homepage.png")
        if os.path.exists(logo_path):
            logo_pix = QPixmap(logo_path)
            # logo高度与标题文字高度匹配，视觉上大小一致
            scaled_logo = logo_pix.scaledToHeight(100, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_logo)
            logo_label.setAlignment(Qt.AlignVCenter)

        # 左右弹簧，整体居中
        title_layout.addStretch()
        title_layout.addWidget(text_group)
        title_layout.addWidget(logo_label)
        title_layout.addStretch()

        # ===== 功能卡片区域（2x2 网格） =====
        cards_widget = QWidget()
        cards_widget.setFixedWidth(720)
        cards_layout = QHBoxLayout(cards_widget)
        cards_layout.setSpacing(24)
        cards_layout.setContentsMargins(0, 0, 0, 0)

        # 第一列
        col1_layout = QVBoxLayout()
        col1_layout.setSpacing(24)

        btn1 = QPushButton("⚡ 电路版图生成")
        btn1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        btn1.clicked.connect(self.jump_to_gen.emit)

        btn2 = QPushButton("⚡ 电路参数优化")
        btn2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        btn2.clicked.connect(self.jump_to_opt.emit)

        col1_layout.addWidget(btn1)
        col1_layout.addWidget(btn2)

        # 第二列
        col2_layout = QVBoxLayout()
        col2_layout.setSpacing(24)

        btn3 = QPushButton("⚡ 自动布局")
        btn3.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        btn3.clicked.connect(self.jump_to_place.emit)

        btn4 = QPushButton("⚡ 自动布线")
        btn4.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        btn4.clicked.connect(self.jump_to_route.emit)

        col2_layout.addWidget(btn3)
        col2_layout.addWidget(btn4)

        cards_layout.addLayout(col1_layout)
        cards_layout.addLayout(col2_layout)

        # 组装主布局：卡片水平居中
        main_layout.addWidget(title_widget)
        main_layout.addWidget(cards_widget, 0, Qt.AlignHCenter)


# ====================== 主窗口 ======================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("parms")
        self.resize(1100, 850)

        self.setObjectName("parms")

        # 设置整体浅色背景
        self.setStyleSheet("QMainWindow { background-color: #f5f7fa; }")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 用堆叠窗口管理器替代标签页，实现页面切换
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # 0号页面：主页
        self.home_page = HomePage()
        self.stack.addWidget(self.home_page)

        # 绑定主页跳转信号
        self.home_page.jump_to_gen.connect(lambda: self.switch_to_page(1))
        self.home_page.jump_to_opt.connect(lambda: self.switch_to_page(2))
        self.home_page.jump_to_place.connect(lambda: self.switch_to_page(3))
        self.home_page.jump_to_route.connect(lambda: self.switch_to_page(4))

        # 初始化四个功能页（首次进入时会重新创建，保证刷新）
        self._init_function_pages()

    def _init_function_pages(self):
        """初始化/刷新四个功能页面，每次调用都会重新创建实例，清空所有参数"""
        # 先移除旧页面（如果存在）
        for i in range(self.stack.count()-1, 0, -1):
            widget = self.stack.widget(i)
            if widget:
                self.stack.removeWidget(widget)
                widget.deleteLater()

        # 1号：电路版图生成
        page1_content = CircuitGenerator()
        page1 = FunctionPageWrapper("电路版图生成", page1_content)
        page1.go_home_signal.connect(self.go_back_home)
        self.stack.addWidget(page1)

        # 2号：电路参数优化
        page2_content = CircuitOptWindow()
        page2 = FunctionPageWrapper("电路参数优化", page2_content)
        page2.go_home_signal.connect(self.go_back_home)
        self.stack.addWidget(page2)

        # 3号：自动布局
        page3_content = AutoLayoutWindow()
        page3 = FunctionPageWrapper("自动布局", page3_content)
        page3.go_home_signal.connect(self.go_back_home)
        self.stack.addWidget(page3)

        # 4号：自动布线
        page4_content = RSMTRoutingWidget()
        page4 = FunctionPageWrapper("自动布线", page4_content)
        page4.go_home_signal.connect(self.go_back_home)
        self.stack.addWidget(page4)

    def switch_to_page(self, index):
        """切换到指定功能页，切换前重新创建所有功能页，保证参数刷新"""
        self._init_function_pages()
        self.stack.setCurrentIndex(index)

    def go_back_home(self):
        """返回主页"""
        self.stack.setCurrentIndex(0)

    def create_empty_page(self, title, message):
        """创建一个带科技感图标和文字的占位页面（保留备用）"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)

        icon_label = QLabel("⚡")
        icon_label.setFont(QFont("WenQuanYi Micro Hei", 48))
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("color: #cbd5e0; margin-bottom: 20px;")

        text_label = QLabel(message)
        text_label.setFont(QFont("WenQuanYi Micro Hei", 16))
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setStyleSheet("color: #718096; background: transparent;")

        layout.addWidget(icon_label)
        layout.addWidget(text_label)
        return page


if __name__ == "__main__":
    icon_path = os.path.join(base_path, "assets", "image.png")
    print(icon_path)
    app = QApplication(sys.argv)
    app.setApplicationName("parms")
    app.setApplicationDisplayName("parms")
    app.setOrganizationName("parms")
    app.setDesktopFileName("parms")

    if os.path.exists(icon_path):
        app_icon = QIcon()
        app_icon.addFile(icon_path, QSize(64, 64))
        app_icon.addFile(icon_path, QSize(128, 128))
        app_icon.addFile(icon_path, QSize(256, 256))
        app.setWindowIcon(app_icon)

    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
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