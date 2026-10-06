import os
import sys
import warnings

if getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.join(sys._MEIPASS, 'site-packages'))


from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QButtonGroup, QSizePolicy
)
from PyQt5.QtGui import (
    QFont, QPalette, QColor, QIcon, QPainter, QPixmap, QPainterPath
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QRectF


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


# ====================== 主页样式与图片控件 ======================

# 蓝色色阶：主色 #2b6ef7 / 深色 #1e3a8a / 浅色 #dbeafe / 边框 #bfdbfe / 背景 #f5f7fa
HOME_STYLE = """
#homePage {
    background-color: #f5f7fa;
}

/* 顶部通栏横幅：主色到深色横向渐变 */
#header {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                      stop:0 #2b6ef7, stop:1 #1e5bbf);
    border-radius: 12px;
}
#headerTitle {
    color: #ffffff;
    font-size: 34px;
    font-weight: bold;
}
#headerSubtitle {
    color: #ffffff;
    font-size: 18px;
}

/* 左侧导航按钮 */
#navBar QPushButton {
    background-color: #dbeafe;
    color: #1e3a8a;
    border: none;
    border-radius: 8px;
    font-size: 15px;
}
#navBar QPushButton:hover {
    background-color: #bfdbfe;
}
#navBar QPushButton:checked {
    background-color: #1e3a8a;
    color: #ffffff;
}

/* 右侧内容区外框 */
#contentFrame {
    background-color: #ffffff;
    border: 2px solid #bfdbfe;
    border-radius: 12px;
}

/* 底部页脚 */
#footer {
    background-color: #1e3a8a;
    color: #ffffff;
    font-size: 12px;
    border-radius: 8px;
}
"""


def circular_pixmap(image_path, size, padding=9):
    """白底圆形徽标：logo 等比缩放后完整放进圈内（不裁剪）"""
    target = QPixmap(size, size)
    target.fill(Qt.transparent)

    painter = QPainter(target)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)

    circle = QPainterPath()
    circle.addEllipse(0, 0, size, size)
    painter.fillPath(circle, QColor("#ffffff"))
    painter.setClipPath(circle)

    src = QPixmap(image_path)
    if not src.isNull():
        inner = size - 2 * padding
        fitted = src.scaled(inner, inner, Qt.KeepAspectRatio,
                            Qt.SmoothTransformation)
        painter.drawPixmap((size - fitted.width()) // 2,
                           (size - fitted.height()) // 2, fitted)
    painter.end()
    return target


class RoundedImage(QWidget):
    """等比缩放铺满容器、按圆角矩形裁剪的图片控件（无留白）"""

    def __init__(self, image_path, radius=10, parent=None):
        super().__init__(parent)
        self._radius = radius
        self._pixmap = QPixmap(image_path)
        self._scaled = None
        self._scaled_for = QSize()

    def paintEvent(self, event):
        if self._pixmap.isNull() or self.width() <= 0 or self.height() <= 0:
            return

        # 原图很大，缩放很贵，只在尺寸变化时重算一次
        if self._scaled is None or self._scaled_for != self.size():
            # 等比放大到能铺满整个容器，再居中裁剪掉多余部分
            self._scaled = self._pixmap.scaled(
                self.size(), Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation)
            self._scaled_for = self.size()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()), self._radius, self._radius)
        painter.setClipPath(clip)

        offset_x = (self._scaled.width() - self.width()) // 2
        offset_y = (self._scaled.height() - self.height()) // 2
        painter.drawPixmap(0, 0, self._scaled,
                           offset_x, offset_y, self.width(), self.height())


# ====================== 主页（HomePage） ======================
class HomePage(QWidget):
    """软件主页：顶部横幅 + 左侧导航 + 右侧图片区 + 底部页脚"""
    # 四个跳转信号，分别对应四个功能
    jump_to_gen = pyqtSignal()
    jump_to_opt = pyqtSignal()
    jump_to_place = pyqtSignal()
    jump_to_route = pyqtSignal()

    # (按钮文字, 对应信号)，顺序即界面上的排列顺序
    NAV_ITEMS = (
        ("电路版图生成", "jump_to_gen"),
        ("自动布局", "jump_to_place"),
        ("电路参数优化", "jump_to_opt"),
        ("自动布线", "jump_to_route"),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("homePage")
        self.setStyleSheet(HOME_STYLE)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(16)

        root_layout.addWidget(self._build_header())
        root_layout.addWidget(self._build_body(), 1)
        root_layout.addWidget(self._build_footer())

    def _build_header(self):
        """顶部横幅：圆形logo与文字作为一个整体水平居中"""
        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(170)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(28, 0, 28, 0)
        header_layout.setSpacing(0)

        logo_label = QLabel()
        logo_label.setFixedSize(104, 104)
        logo_path = os.path.join(base_path, "assets", "homepage.png")
        if os.path.exists(logo_path):
            logo_label.setPixmap(circular_pixmap(logo_path, 104))

        title_label = QLabel("模拟电路自动化设计工具")
        title_label.setObjectName("headerTitle")

        version_label = QLabel("Parms")
        version_label.setObjectName("headerSubtitle")

        # 副标题放在主标题正下方，两行文字居中
        text_group = QWidget()
        text_layout = QVBoxLayout(text_group)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)
        text_layout.addWidget(title_label, 0, Qt.AlignHCenter)
        text_layout.addWidget(version_label, 0, Qt.AlignHCenter)

        header_layout.addStretch()
        header_layout.addWidget(logo_label, 0, Qt.AlignVCenter)
        header_layout.addSpacing(26)
        header_layout.addWidget(text_group, 0, Qt.AlignVCenter)
        header_layout.addStretch()
        return header

    def _build_body(self):
        """主体区域：左侧固定导航栏 + 右侧自适应图片区"""
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(16)

        body_layout.addWidget(self._build_nav())

        content_frame = QFrame()
        content_frame.setObjectName("contentFrame")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(2, 2, 2, 2)
        content_layout.setSpacing(0)
        content_layout.addWidget(
            RoundedImage(os.path.join(base_path, "xpian.png"), radius=10)
        )

        body_layout.addWidget(content_frame, 1)
        return body

    def _build_nav(self):
        """左侧导航栏：四个功能按钮，在整列内均匀分布"""
        nav_bar = QWidget()
        nav_bar.setObjectName("navBar")
        nav_bar.setFixedWidth(280)

        nav_layout = QVBoxLayout(nav_bar)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(18)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        # 按钮之间只留固定间距，整列由按钮平分撑满，
        # 这样四个按钮的上下边正好和右侧图片区对齐（不用弹簧，否则间隔会大到 70px 以上）
        for text, signal_name in self.NAV_ITEMS:
            button = QPushButton(text)
            button.setCheckable(True)
            button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(getattr(self, signal_name).emit)
            self.nav_group.addButton(button)
            nav_layout.addWidget(button)
        return nav_bar

    def clear_nav_selection(self):
        """取消导航栏的选中态：避免看起来像默认选中了某一项"""
        # 互斥的 QButtonGroup 不允许直接取消选中，得先临时关掉互斥
        self.nav_group.setExclusive(False)
        for button in self.nav_group.buttons():
            button.setChecked(False)
        self.nav_group.setExclusive(True)

    def _build_footer(self):
        """底部页脚"""
        footer = QLabel("版本 v0.6 | 团队：CEDA | WHUT")
        footer.setObjectName("footer")
        footer.setFixedHeight(36)
        footer.setAlignment(Qt.AlignCenter)
        return footer


# ====================== 顶部菜单栏 ======================
# (菜单名, [条目, ...])，条目为 None 表示分隔线。
# 目前只做展示，条目都还没接实际功能。
MENU_ITEMS = (
    ("文件（F）", ("打开网表…", "打开结果目录", None, "退出")),
    ("编辑（E）", ("撤销", "重做", None, "清除执行日志")),
    ("构建（B）", ("一键运行全部流程", None, "网表转 DGL 图", "提取匹配约束",
                  "运行自动布局优化", "运行自动布线")),
    ("工具（T）", ("打开工作目录", None, "首选项…")),
    ("窗口（W）", ("主页", None, "电路版图生成", "电路参数优化", "自动布局", "自动布线")),
    ("帮助（H）", ("使用说明", None, "关于 parms")),
)


# ====================== 主窗口 ======================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("parms")
        self.resize(1120, 760)

        self.setObjectName("parms")

        # 整体浅色背景 + 菜单栏/下拉菜单样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f7fa;
            }
            QMenuBar {
                background-color: #e9edf2;
                border-bottom: 1px solid #dcdfe6;
                padding: 2px 6px;
                font-size: 13px;
                color: #303133;
            }
            QMenuBar::item {
                background: transparent;
                color: #303133;
                padding: 5px 5px;
                border-radius: 6px;
            }
            QMenuBar::item:selected, QMenuBar::item:pressed {
                background-color: #dbeafe;
                color: #1e3a8a;
            }
            QMenu {
                background-color: #ffffff;
                border: 1px solid #e4e7ed;
                border-radius: 8px;
                padding: 4px;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 26px 6px 16px;
                border-radius: 6px;
                color: #303133;
            }
            QMenu::item:selected {
                background-color: #dbeafe;
                color: #1e3a8a;
            }
            QMenu::separator {
                height: 1px;
                background-color: #e4e7ed;
                margin: 4px 8px;
            }
        """)

        self.build_menu_bar()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 用堆叠窗口管理器替代标签页，实现页面切换
        # 忽略各功能页自身的尺寸要求，否则隐藏页会把主窗口顶大，1200x800 压不下去
        self.stack = QStackedWidget()
        self.stack.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
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

    def build_menu_bar(self):
        """顶部菜单栏：目前只展示，条目还没接实际功能"""
        menu_bar = self.menuBar()
        # 强制用窗口内菜单栏，免得某些桌面环境把它挪到系统全局顶栏去
        menu_bar.setNativeMenuBar(False)

        for title, items in MENU_ITEMS:
            menu = menu_bar.addMenu(title)
            for text in items:
                if text is None:
                    menu.addSeparator()
                else:
                    menu.addAction(text)

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
        # 回到主页时清掉导航栏的加深状态，只有刚点下去那一下才高亮
        self.home_page.clear_nav_selection()
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
    #print(icon_path)
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