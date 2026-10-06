"""自动布线工作台。

左侧文件树浏览 + 右侧标签区阅读，一个「一键生成」串起三个阶段：
RSMT 斯坦纳树计算 → 走线间距合法化 → GDS 版图生成。
界面看着是一步完成，内部仍然是逐级推进、上一级产出直接喂给下一级。

界面替代了老的 routing_ui.RSMTRoutingWidget（那个是三个割裂的标签页，
要手动点三次、手动选三次文件）。routing_ui.py 里那些算法函数仍然照常复用。
"""

import os
import sys
import time
import traceback

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QFileDialog, QTreeWidget, QTreeWidgetItem, QTabWidget, QPlainTextEdit,
    QFrame, QTabBar, QMenu, QMessageBox,
)
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal

import matplotlib

matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
from matplotlib.figure import Figure

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# rsmt_router 目录：routing_ui 需要它来找 UnionFind / gdsii
sys.path.append(BASE_DIR)
# 项目根目录：为了 import ui_style 和 rsmt_router 包
sys.path.append(os.path.dirname(BASE_DIR))

from ui_style import PAGE_STYLE, cjk_font_properties
from gds_viewer import GdsViewer
from rsmt_router import pipeline
from rsmt_router.routing_ui import display_plot_inside

# 阶段的显示名
STAGE_LABELS = {
    "step1": "阶段1 RSMT斯坦纳树",
    "step2": "阶段2 间距合法化",
    "step3": "阶段3 GDS生成",
}

# 后台线程的存活引用：页面被销毁时 QThread 若还在跑会直接崩，
# 放模块级集合里托管，线程跑完再移除
_ACTIVE_WORKERS = set()


class RoutingWorker(QThread):
    """后台跑完整条流水线，避免界面卡住"""

    stage_done = pyqtSignal(str, object)   # (阶段名, 结果字典)
    logged = pyqtSignal(str)               # 一行日志
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, nets_path, layout_txt, out_dir,
                 reuse_step1=None, reuse_step2=None):
        super().__init__()
        self.nets_path = nets_path
        self.layout_txt = layout_txt
        self.out_dir = out_dir
        self.reuse_step1 = reuse_step1
        self.reuse_step2 = reuse_step2

    def run(self):
        try:
            result = pipeline.run_all(
                self.nets_path, self.layout_txt, self.out_dir,
                on_stage=lambda stage, payload: self.stage_done.emit(stage, payload),
                log=self.logged.emit,
                reuse_step1=self.reuse_step1,
                reuse_step2=self.reuse_step2,
            )
            self.succeeded.emit(result)
        except Exception:
            self.failed.emit(traceback.format_exc())


class RoutingPage(QWidget):
    """自动布线工作台"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        self.setStyleSheet(PAGE_STYLE)

        self.worker = None
        self.start_time = 0.0
        # 三个阶段各自建子目录，直接放在 rsmt_router 下面，
        # 这样左边文件树就是磁盘上的真实目录结构
        self.out_dir = BASE_DIR
        self.nets_path = os.path.join(BASE_DIR, "nets.txt")
        self.layout_path = os.path.join(BASE_DIR, "CP_OP2.txt")

        self.build_ui()
        self.refresh_tree()

    # ==================== 界面搭建 ====================
    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(9)

        root.addWidget(self.build_toolbar())

        body = QHBoxLayout()
        body.setSpacing(9)
        body.addWidget(self.build_file_tree())
        body.addWidget(self.build_tabs(), 1)
        root.addLayout(body, 1)

    def build_toolbar(self):
        box = QFrame()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(6)

        # 全部挤在一行：主按钮 + 网表 + 布局 + 高级开关 + 状态
        row = QHBoxLayout()
        row.setSpacing(6)

        self.run_btn = QPushButton("▶ 一键生成")
        self.run_btn.setObjectName("primaryButton")
        self.run_btn.setMinimumHeight(30)
        self.run_btn.setFixedWidth(120)
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.clicked.connect(self.run_pipeline)
        row.addWidget(self.run_btn)

        row.addWidget(QLabel("网表："))
        self.nets_edit = QLineEdit(self.nets_path)
        self.nets_edit.setReadOnly(True)
        row.addWidget(self.nets_edit, 1)
        nets_btn = QPushButton("选择")
        nets_btn.setFixedWidth(52)
        nets_btn.clicked.connect(self.choose_nets)
        row.addWidget(nets_btn)

        row.addWidget(QLabel("布局："))
        self.layout_edit = QLineEdit(self.layout_path)
        self.layout_edit.setReadOnly(True)
        row.addWidget(self.layout_edit, 1)
        layout_btn = QPushButton("选择")
        layout_btn.setFixedWidth(52)
        layout_btn.clicked.connect(self.choose_layout)
        row.addWidget(layout_btn)

        self.advanced_btn = QPushButton("▸ 高级")
        self.advanced_btn.setObjectName("entryButton")
        self.advanced_btn.setCheckable(True)
        self.advanced_btn.setCursor(Qt.PointingHandCursor)
        self.advanced_btn.setFixedWidth(68)
        self.advanced_btn.toggled.connect(self.toggle_advanced)
        row.addWidget(self.advanced_btn)

        self.status_label = QLabel("就绪")
        self.status_label.setToolTip("运行状态")
        row.addWidget(self.status_label)
        layout.addLayout(row)

        # 可折叠的高级区
        self.advanced_panel = self.build_advanced_panel()
        self.advanced_panel.setVisible(False)
        layout.addWidget(self.advanced_panel)

        return box

    def build_advanced_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(6)

        row, self.reuse_step1_edit = self.path_row(
            "复用阶段1结果：", "（留空则现场计算）", self.choose_reuse_step1)
        layout.addLayout(row)

        row, self.reuse_step2_edit = self.path_row(
            "复用阶段2结果：", "（留空则现场计算）", self.choose_reuse_step2)
        layout.addLayout(row)

        layout.addWidget(QLabel(
            "指定了现成结果文件就跳过对应阶段、直接拿它往下走；"
            "被跳过的阶段不会出布线图。"))
        return panel

    @staticmethod
    def path_row(label, placeholder, on_browse):
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(QLabel(label))
        edit = QLineEdit()
        edit.setReadOnly(True)
        edit.setPlaceholderText(placeholder)
        row.addWidget(edit, 1)

        browse = QPushButton("选择")
        browse.clicked.connect(on_browse)
        row.addWidget(browse)

        clear = QPushButton("清除")
        clear.clicked.connect(edit.clear)
        row.addWidget(clear)
        return row, edit

    def build_file_tree(self):
        """左边：一个刷新按钮 + 磁盘真实目录树"""
        panel = QWidget()
        panel.setFixedWidth(272)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(2, 0, 0, 0)
        header.addWidget(QLabel("文件目录"))
        header.addStretch()
        refresh = QPushButton("↻ 刷新")
        refresh.setObjectName("entryButton")
        refresh.setCursor(Qt.PointingHandCursor)
        refresh.setToolTip("重新读取磁盘上的实际目录")
        refresh.clicked.connect(self.refresh_tree)
        header.addWidget(refresh)
        layout.addLayout(header)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setColumnCount(1)
        self.tree.itemClicked.connect(self.on_tree_click)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.on_tree_context_menu)
        layout.addWidget(self.tree, 1)
        return panel

    def build_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        # 同上：点标签也把焦点从文件树抢过来
        self.tabs.tabBar().setFocusPolicy(Qt.ClickFocus)
        self.tabs.tabCloseRequested.connect(self.close_tab)

        self.plot_view = self.build_plot_view()
        self.log_view = self.build_log_view()
        self.tabs.addTab(self.plot_view, "布线图")
        self.tabs.addTab(self.log_view, "日志")
        self.hide_fixed_tab_close_buttons()
        return self.tabs

    def build_plot_view(self):
        view = QWidget()
        # 点图区要能把焦点从左边文件树上抢过来，
        # 这样树里那个选中项才会按「失去焦点」显示成浅灰
        view.setFocusPolicy(Qt.ClickFocus)
        layout = QVBoxLayout(view)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self.figure = Figure(figsize=(8, 4))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(280)
        self.canvas.setFocusPolicy(Qt.ClickFocus)
        self.nav_toolbar = NavigationToolbar2QT(self.canvas, view)

        layout.addWidget(self.nav_toolbar)
        layout.addWidget(self.canvas, 1)

        # 左右两幅：左=原始斯坦纳森林，右=间距合法化后
        self.ax_raw = self.figure.add_subplot(1, 2, 1)
        self.ax_legalized = self.figure.add_subplot(1, 2, 2)
        self.reset_plot()
        return view

    def build_log_view(self):
        self.log_view_widget = QPlainTextEdit()
        self.log_view_widget.setReadOnly(True)
        self.log_view_widget.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.log_view_widget.setPlaceholderText("运行日志会显示在这里…")
        return self.log_view_widget

    def hide_fixed_tab_close_buttons(self):
        """布线图 / 日志 是常驻标签，把它们的关闭按钮去掉"""
        bar = self.tabs.tabBar()
        for index in (0, 1):
            bar.setTabButton(index, QTabBar.RightSide, None)

    # ==================== 文件树 ====================
    def refresh_tree(self):
        """按磁盘上的真实结构重建目录树。

        以 rsmt_router 为根，只罗列这三步相关的目录（step1_rsmt /
        step2_legalize / step3_gds）和两个输入文件；rsmt_router 里的
        源码、storey、gdsii 等无关内容不显示。
        目录里实际有什么文件就显示什么，手动往里放文件也会同步出来。
        """
        self.tree.clear()

        root = QTreeWidgetItem([os.path.basename(BASE_DIR)])
        root.setToolTip(0, BASE_DIR)

        inputs = QTreeWidgetItem(["输入文件"])
        self.add_file_item(inputs, os.path.basename(self.nets_path), self.nets_path)
        self.add_file_item(inputs, os.path.basename(self.layout_path), self.layout_path)
        root.addChild(inputs)

        for dirname in pipeline.STAGE_DIRS.values():
            stage_dir = os.path.join(self.out_dir, dirname)
            node = QTreeWidgetItem([dirname])
            node.setToolTip(0, stage_dir)
            if os.path.isdir(stage_dir):
                self.populate_dir(node, stage_dir, depth=1)
            else:
                # 还没生成过，灰着显示目标目录
                node.setForeground(0, QBrush(QColor("#a8abb2")))
            root.addChild(node)

        self.tree.addTopLevelItem(root)
        # 展开必须放在加进树之后，否则加顶层节点时展开状态会被重置
        self.tree.expandAll()

    def populate_dir(self, parent, path, depth=1, max_depth=3):
        """把一个真实目录的内容挂到树上（最多 3 层，免得符号链接绕圈）"""
        try:
            entries = sorted(os.listdir(path))
        except OSError:
            return

        dirs = [e for e in entries if os.path.isdir(os.path.join(path, e))]
        files = [e for e in entries if not os.path.isdir(os.path.join(path, e))]
        for name in dirs + files:
            full = os.path.join(path, name)
            if os.path.isdir(full):
                child = QTreeWidgetItem([name + "/"])
                child.setToolTip(0, full)
                if depth < max_depth:
                    self.populate_dir(child, full, depth + 1, max_depth)
                parent.addChild(child)
            else:
                self.add_file_item(parent, name, full)

    def add_file_item(self, parent, label, path):
        item = QTreeWidgetItem([label])
        item.setData(0, Qt.UserRole, path)
        item.setToolTip(0, path)
        parent.addChild(item)

    def on_tree_click(self, item, _column):
        path = item.data(0, Qt.UserRole)
        if path:
            self.open_file_tab(path)

    # ==================== 右键删除 ====================
    def on_tree_context_menu(self, pos):
        """右键菜单：只给「文件」项提供删除，目录和分组节点不给"""
        item = self.tree.itemAt(pos)
        if item is None:
            return
        path = item.data(0, Qt.UserRole)
        if not path or not os.path.isfile(path):
            return                      # 目录/分组节点：不弹菜单

        menu = QMenu(self)
        delete_action = menu.addAction(f"删除  {item.text(0)}")
        # 用 singleShot 推迟一拍再弹确认框：菜单的 triggered 是在 menu.exec_()
        # 的嵌套事件循环里发出来的，直接在里面开模态框会套两层循环，
        # 关闭时得等菜单那层先解开，表现出来就是点了按钮一两秒才消失。
        delete_action.triggered.connect(
            lambda: QTimer.singleShot(0, lambda: self.delete_file(path)))
        menu.exec_(self.tree.viewport().mapToGlobal(pos))

    def delete_file(self, path):
        """删除一个文件（会先确认）。目录不在此列。"""
        if not os.path.isfile(path):
            return

        answer = QMessageBox.question(
            self, "删除文件",
            f"确定删除这个文件吗？删除后无法恢复。\n\n{path}",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        try:
            os.remove(path)
        except OSError as exc:
            QMessageBox.warning(self, "删除失败", f"无法删除：\n{path}\n\n{exc}")
            return

        # 这个文件可能正开在标签里，把那个标签一并关掉，免得留下已删除的内容
        for index in range(self.tabs.count() - 1, -1, -1):
            if self.tabs.tabBar().tabData(index) == path:
                self.close_tab(index)
                break

        self.append_log(f"已删除文件：{path}")
        self.refresh_tree()

    # ==================== 标签页 ====================
    def open_file_tab(self, path):
        # 已经开着就切过去，不重复开
        # tabData 挂在 QTabBar 上，QTabWidget 本身没有这个方法
        for index in range(self.tabs.count()):
            if self.tabs.tabBar().tabData(index) == path:
                self.tabs.setCurrentIndex(index)
                return

        if path.lower().endswith(".gds"):
            # GDS 走版图查看器：按层着色渲染 + 图层面板，不是文本
            widget = GdsViewer(path)
        else:
            widget = QPlainTextEdit()
            widget.setReadOnly(True)
            widget.setLineWrapMode(QPlainTextEdit.NoWrap)
            widget.setPlainText(self.read_as_text(path))

        index = self.tabs.addTab(widget, os.path.basename(path))
        self.tabs.tabBar().setTabData(index, path)
        self.tabs.setCurrentIndex(index)
        self.hide_fixed_tab_close_buttons()

    @staticmethod
    def read_as_text(path):
        """读文件内容用于显示（.gds 走 GdsViewer，不会走到这里）"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            size = os.path.getsize(path)
            return f"{os.path.basename(path)} 不是 UTF-8 文本（{size} 字节），无法显示。"
        except OSError as exc:
            return f"读取失败：{exc}"

    def close_tab(self, index):
        widget = self.tabs.widget(index)
        if widget in (self.plot_view, self.log_view):
            return                      # 常驻标签不给关
        self.tabs.removeTab(index)
        widget.deleteLater()
        self.hide_fixed_tab_close_buttons()

    # ==================== 布线图 ====================
    def reset_plot(self):
        self.draw_placeholder(self.ax_raw, "原始斯坦纳森林")
        self.draw_placeholder(self.ax_legalized, "间距合法化后")
        self.figure.subplots_adjust(left=0.07, right=0.98, top=0.90,
                                    bottom=0.10, wspace=0.18)
        self.canvas.draw_idle()

    def draw_placeholder(self, ax, title):
        ax.clear()
        ax.set_title(title, fontsize=11, color="#94a3b8",
                     fontproperties=cjk_font_properties())
        ax.text(0.5, 0.5, "等待生成…", ha="center", va="center", fontsize=10,
                color="#cbd5e0", fontproperties=cjk_font_properties())
        ax.set_axis_off()

    def draw_panel(self, ax, title, payload):
        ax.clear()
        ax.set_axis_on()
        display_plot_inside(ax, payload.get("pins"), payload.get("steiner_points"),
                            payload["steiner_trees"])
        ax.set_title(title, fontsize=11, fontproperties=cjk_font_properties())
        self.figure.subplots_adjust(left=0.07, right=0.98, top=0.90,
                                    bottom=0.10, wspace=0.18)
        self.canvas.draw_idle()

    # ==================== 文件选择 ====================
    def choose_nets(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择网表文件", BASE_DIR, "文本文件 (*.txt);;所有文件 (*.*)")
        if path:
            self.nets_path = path
            self.nets_edit.setText(path)
            self.refresh_tree()

    def choose_layout(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择布局文件", BASE_DIR, "文本文件 (*.txt);;所有文件 (*.*)")
        if path:
            self.layout_path = path
            self.layout_edit.setText(path)
            self.refresh_tree()

    def choose_reuse_step1(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择阶段1结果文件", self.out_dir, "文本文件 (*.txt);;所有文件 (*.*)")
        if path:
            self.reuse_step1_edit.setText(path)

    def choose_reuse_step2(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择阶段2结果文件", self.out_dir, "文本文件 (*.txt);;所有文件 (*.*)")
        if path:
            self.reuse_step2_edit.setText(path)

    def toggle_advanced(self, checked):
        self.advanced_panel.setVisible(checked)
        self.advanced_btn.setText("▾ 高级" if checked else "▸ 高级")

    # ==================== 运行 ====================
    def run_pipeline(self):
        if self.worker is not None and self.worker.isRunning():
            self.append_log("已有任务在运行中，请等它结束")
            return

        nets = self.nets_edit.text().strip()
        layout = self.layout_edit.text().strip()
        if not os.path.exists(nets):
            self.append_log(f"网表文件不存在：{nets}")
            self.tabs.setCurrentWidget(self.log_view)
            return
        if not os.path.exists(layout):
            self.append_log(f"布局文件不存在：{layout}")
            self.tabs.setCurrentWidget(self.log_view)
            return

        self.log_view_widget.clear()
        self.reset_plot()
        self.tabs.setCurrentWidget(self.plot_view)

        self.start_time = time.time()
        self.run_btn.setEnabled(False)
        self.run_btn.setText("⏳ 正在生成…")
        self.status_label.setText("⏳ 运行中…")

        worker = RoutingWorker(
            nets, layout, self.out_dir,
            reuse_step1=self.reuse_step1_edit.text().strip() or None,
            reuse_step2=self.reuse_step2_edit.text().strip() or None,
        )
        self.worker = worker
        _ACTIVE_WORKERS.add(worker)
        worker.finished.connect(lambda: _ACTIVE_WORKERS.discard(worker))

        worker.logged.connect(self.append_log)
        worker.stage_done.connect(self.on_stage_done)
        worker.succeeded.connect(self.on_succeeded)
        worker.failed.connect(self.on_failed)
        worker.finished.connect(self.on_worker_finished)
        worker.start()

    def append_log(self, message):
        self.log_view_widget.appendPlainText(message)

    def on_stage_done(self, stage, payload):
        """某个阶段跑完：刷新文件树，并把该阶段的走线画到对应那幅图上"""
        self.refresh_tree()
        if payload.get("reused"):
            self.append_log(f"（{STAGE_LABELS[stage]} 复用现成结果，不重绘）")
            return
        if stage == "step1":
            self.draw_panel(self.ax_raw, "原始斯坦纳森林", payload)
        elif stage == "step2":
            self.draw_panel(self.ax_legalized, "间距合法化后", payload)

    def on_succeeded(self, result):
        elapsed = time.time() - self.start_time
        step1 = result.get("step1", {})
        step2 = result.get("step2", {})
        step3 = result.get("step3", {})

        self.append_log("")
        self.append_log(f"全部完成，总耗时 {elapsed:.2f} 秒")
        if step1.get("total_length") is not None:
            self.append_log(
                f"  阶段1：总线长 {step1['total_length']:.1f}，"
                f"通孔 {len(step1.get('via_points', []))} 个")
        if step2.get("added_length") is not None:
            self.append_log(
                f"  阶段2：迭代 {step2.get('rounds')} 轮，"
                f"合法化新增线长 {step2['added_length']:.2f}")
        if step3.get("segments") is not None:
            self.append_log(f"  阶段3：写入走线 {step3['segments']} 段")

        self.status_label.setText(f"✔ 完成 {elapsed:.2f} 秒")
        self.tabs.setCurrentWidget(self.plot_view)

    def on_failed(self, error_text):
        elapsed = time.time() - self.start_time
        self.append_log("")
        self.append_log(f"运行失败（{elapsed:.2f} 秒）：")
        self.append_log(error_text)
        self.status_label.setText("✘ 运行失败")
        self.tabs.setCurrentWidget(self.log_view)

    def on_worker_finished(self):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("▶ 一键生成")
        if self.worker is not None:
            self.worker.deleteLater()
            self.worker = None


# 模块可以独立运行测试
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtGui import QFont

    app = QApplication(sys.argv)
    font = QFont("WenQuanYi Micro Hei")
    font.setPointSize(10)
    app.setFont(font)

    window = RoutingPage()
    window.setWindowTitle("自动布线")
    window.resize(1120, 700)
    window.show()
    sys.exit(app.exec_())
