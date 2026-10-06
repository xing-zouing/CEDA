"""各功能页共用的界面样式与绘图字体。

配色跟主页保持一致：
主色 #2b6ef7 / 深色 #1e3a8a / 浅色 #dbeafe / 边框 #dcdfe6 / 页面底 #f5f7fa
"""

import os

# matplotlib 的字体扫描认不出 .ttc，字体缓存里根本没有文泉驿，
# 图上写中文会变成方块。这里按路径手动注册一份，只在需要中文的地方用，
# 不去改全局 rcParams（项目里好几个模块都在用 matplotlib，改全局会影响它们的图）。
_CJK_FONT_PATHS = (
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
)
_cjk_font_prop = None
_cjk_font_loaded = False


def cjk_font_properties():
    """返回文泉驿字体的 FontProperties；系统里没有就返回 None（用默认字体）"""
    global _cjk_font_prop, _cjk_font_loaded
    if not _cjk_font_loaded:
        _cjk_font_loaded = True
        from matplotlib import font_manager
        for path in _CJK_FONT_PATHS:
            if os.path.exists(path):
                font_manager.fontManager.addfont(path)
                _cjk_font_prop = font_manager.FontProperties(fname=path)
                break
    return _cjk_font_prop


PAGE_STYLE = """
#page {
    background-color: #f5f7fa;
}

QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e4e7ed;
    border-radius: 10px;
    margin-top: 13px;
    padding: 10px 8px 8px 8px;
    font-size: 13px;
    font-weight: bold;
    color: #1e3a8a;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
}

QLabel {
    color: #606266;
    font-size: 12px;
    font-weight: normal;
}

QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    border: 1px solid #dcdfe6;
    border-radius: 6px;
    min-height: 20px;
    color: #1a202c;
    font-size: 12px;
    selection-background-color: #2b6ef7;
    selection-color: #ffffff;
}
QLineEdit {
    padding: 4px 8px;
}
/* 数字框右侧得给上下箭头留出固定宽度，否则箭头会被 padding 挤变形 */
QSpinBox, QDoubleSpinBox {
    padding: 4px 2px 4px 8px;
}
QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 18px;
    margin: 1px 1px 0 0;
    border-left: 1px solid #e4e7ed;
    border-top-right-radius: 5px;
    background-color: #f5f7fa;
}
QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 18px;
    margin: 0 1px 1px 0;
    border-left: 1px solid #e4e7ed;
    border-bottom-right-radius: 5px;
    background-color: #f5f7fa;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #dbeafe;
}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow,
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
    width: 7px;
    height: 7px;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #2b6ef7;
}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {
    background-color: #f5f7fa;
    color: #a8abb2;
}

QPushButton {
    background-color: #f5f7fa;
    border: 1px solid #dcdfe6;
    border-radius: 6px;
    padding: 5px 14px;
    color: #606266;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #ecf5ff;
    border-color: #2b6ef7;
    color: #2b6ef7;
}
QPushButton:pressed {
    background-color: #dbeafe;
}
QPushButton:disabled {
    background-color: #f5f7fa;
    border-color: #e4e7ed;
    color: #a8abb2;
}

/* 主操作按钮：浅蓝，不抢眼 */
QPushButton#primaryButton {
    background-color: #dbeafe;
    border: 1px solid #bfdbfe;
    border-radius: 8px;
    color: #1e3a8a;
    font-size: 13px;
    font-weight: bold;
    padding: 6px 22px;
}
QPushButton#primaryButton:hover {
    background-color: #bfdbfe;
    border-color: #93c5fd;
}
QPushButton#primaryButton:pressed {
    background-color: #a9cefd;
}
QPushButton#primaryButton:disabled {
    background-color: #eef4ff;
    border-color: #dbeafe;
    color: #a8abb2;
}

/* 顶部入口 / 返回按钮：和主页导航按钮同色系 */
QPushButton#entryButton {
    background-color: #dbeafe;
    border: none;
    border-radius: 8px;
    color: #1e3a8a;
    font-size: 12px;
    font-weight: bold;
    padding: 6px 14px;
}
QPushButton#entryButton:hover {
    background-color: #bfdbfe;
}
QPushButton#entryButton:pressed {
    background-color: #bfdbfe;
}

/* 紧凑按钮：用在空间紧张的地方（比如版图查看器的图层面板），
   和 entryButton 同色系，但内边距小很多，两个汉字也放得下 */
QPushButton#compactButton {
    background-color: #dbeafe;
    border: none;
    border-radius: 6px;
    color: #1e3a8a;
    font-size: 11px;
    font-weight: bold;
    padding: 5px 5px;
}
QPushButton#compactButton:hover {
    background-color: #bfdbfe;
}
QPushButton#compactButton:pressed {
    background-color: #a9cefd;
}

QTextEdit, QPlainTextEdit {
    background-color: #fbfcfe;
    border: 1px solid #e4e7ed;
    border-radius: 8px;
    padding: 4px 6px;
    font-family: "WenQuanYi Micro Hei", monospace;
    font-size: 11px;
    color: #475569;
}

/* 左侧文件树 */
QTreeWidget {
    background-color: #ffffff;
    border: 1px solid #e4e7ed;
    border-radius: 10px;
    padding: 4px;
    font-size: 12px;
    color: #303133;
    outline: none;
}
QTreeWidget::item {
    height: 24px;
    border-radius: 6px;
}
QTreeWidget::item:hover {
    background-color: #f0f6ff;
}
QTreeWidget::item:selected {
    background-color: #dbeafe;
    color: #1e3a8a;
}
/* 焦点移到别处（点了右边图区/标签/按钮）但选中项没变时，
   用浅灰表示「还选着，但不是当前焦点」，避免蓝块一直杵在那儿 */
QTreeWidget::item:selected:!active {
    background-color: #e9edf2;
    color: #606266;
}
/* 缩进/展开箭头那一列 Qt 会用调色板里的高亮色单独刷一遍，
   不覆盖的话选中行左边会多出一块深蓝 */
QTreeWidget::branch:selected {
    background-color: #dbeafe;
}
QTreeWidget::branch:selected:!active {
    background-color: #e9edf2;
}

/* 右侧标签区 */
QTabWidget::pane {
    background-color: #ffffff;
    border: 1px solid #e4e7ed;
    border-radius: 10px;
    top: -1px;
}
QTabBar::tab {
    background-color: #eef1f5;
    border: 1px solid #e4e7ed;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 6px 14px;
    margin-right: 3px;
    font-size: 12px;
    color: #606266;
}
QTabBar::tab:hover {
    background-color: #e3ecfa;
    color: #1e3a8a;
}
QTabBar::tab:selected {
    background-color: #ffffff;
    color: #1e3a8a;
    font-weight: bold;
}
QTabBar::close-button {
    subcontrol-position: right;
}
"""
