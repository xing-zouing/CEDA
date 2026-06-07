from PyQt5.QtWidgets import (QMainWindow, QMessageBox, QFileDialog,
                             QButtonGroup, QProgressBar,QWidget)
from PyQt5.QtCore import Qt
from PyQt5 import uic
import sys,os

"""内置ui
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)
    
class CircuitUI(QMainWindow):

    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi(resource_path("devise.ui"))"""

"""外置ui"""
class CircuitUI(QWidget):
    """用户界面管理类"""
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi("device_generation/devise.ui", self)
###

        self.current_subckt = ""
        self.ui.stackedWidget.setCurrentIndex(self.ui.comboBox.currentIndex())
        self.setup_progress_bar()
        self.setup_radio_groups()
        self.ui.comboBoxTech.clear()
        ##self.ui.show()

    def setup_progress_bar(self):
        """设置进度条"""
        self.progress_bar = self.ui.progressBar
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setFormat("%v/%m")
        self.progress_bar.hide()

    def setup_radio_groups(self):
        # OD25相关单选按钮组
        self.od25_radio_group = QButtonGroup()
        self.od25_radio_group.addButton(self.ui.radioButton)
        self.od25_radio_group.addButton(self.ui.radioButton_2)
        self.od25_radio_group.addButton(self.ui.radioButton_5)
        self.od25_radio_group.setExclusive(True)

        # MOS类型单选按钮组
        self.mos_type_group = QButtonGroup()
        self.mos_type_group.addButton(self.ui.radioButton_3)  # NMOS
        self.mos_type_group.addButton(self.ui.radioButton_4)  # PMOS
        self.mos_type_group.setExclusive(True)

    def connect_signals(self, handlers):
        """连接UI信号到外部处理函数

        Args:
            handlers: 包含处理函数的字典，应有以下键：
                - generate_component: 生成组件按钮处理函数
                - generate_capacitor: 生成电容按钮处理函数
                - generate_mosfet: 生成MOSFET按钮处理函数
                - generate_from_netlist: 从网表生成按钮处理函数
        """
        # 组件生成按钮
        self.ui.pushButton.clicked.connect(handlers.get('generate_component'))
        self.ui.pushButton_2.clicked.connect(handlers.get('generate_capacitor'))
        self.ui.pushButton_3.clicked.connect(handlers.get('generate_mosfet'))

        # 网表文件选择
        self.ui.pushButtonSelectNetlist.clicked.connect(self.on_select_netlist)
        self.ui.pushButtonSelectTechDir.clicked.connect(self.on_select_tech_dir)
        self.ui.pushButtonGenerate.clicked.connect(handlers.get('generate_from_netlist'))

        # 下拉框变化
        self.ui.comboBox.currentIndexChanged.connect(
            lambda: self.ui.stackedWidget.setCurrentIndex(self.ui.comboBox.currentIndex())
        )

        # 复选框状态变化
        self.ui.checkBox.stateChanged.connect(self.on_od25_state_changed)
        self.ui.radioButton_3.toggled.connect(self.on_mos_type_changed)

    def on_select_netlist(self):
        """选择网表文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.ui,
            "选择网表文件",
            "",
            "Spice网表 (*.sp);;所有文件 (*)"
        )
        if file_path:
            self.ui.lineEditNetlist.setText(file_path)
            return file_path
        return None

    def on_select_tech_dir(self):
        dir_path = QFileDialog.getExistingDirectory(
            self.ui,
            "选择工艺文件目录",
            ""
        )
        if dir_path:
            self.ui.lineEditTechDir.setText(dir_path)
            self.refresh_tech_combo(dir_path)
            return dir_path
        return None

    def refresh_tech_combo(self, tech_dir):
        """刷新工艺文件下拉框"""
        self.ui.comboBoxTech.clear()
        if not os.path.exists(tech_dir):
            return

        # 过滤工艺相关文件
        tech_files = [
            f for f in os.listdir(tech_dir)
            if os.path.isfile(os.path.join(tech_dir, f))
               and f.endswith(('.techfile', '.lef', '.gds'))
        ]
        self.ui.comboBoxTech.addItems(tech_files)

    def on_od25_state_changed(self, is_checked):
        """OD25复选框状态变化处理"""
        if not is_checked:
            self.od25_radio_group.setExclusive(False)
            for btn in self.od25_radio_group.buttons():
                btn.setChecked(False)
            self.od25_radio_group.setExclusive(True)

    def on_mos_type_changed(self, is_checked):
        """MOS类型变化处理"""
        if not is_checked:
            self.ui.checkBox_2.setChecked(False)

    def get_resistor_params(self):
        """获取电阻参数"""
        return {
            'series': self.ui.comboBox_2.currentText() == "True",
            'name': self.ui.lineEdit_4.text().strip(),
            'width': self.ui.lineEdit_6.text().strip(),
            'length': self.ui.lineEdit_3.text().strip(),
            'segments': self.ui.lineEdit_7.text().strip(),
            'seg_space': self.ui.lineEdit_5.text().strip() or "0.18",
            'attr': ['wo' if self.ui.radioButton_7.isChecked() else 'm']
        }

    def get_capacitor_params(self):
        """获取电容参数"""
        return {
            'name': self.ui.lineEdit.text().strip(),
            'width': self.ui.lineEdit_2.text().strip(),
            'length': self.ui.lineEdit_8.text().strip(),
            'spacing': self.ui.lineEdit_9.text().strip(),
            'nf': self.ui.lineEdit_10.text().strip(),
            'm_bot': int(self.ui.comboBox_10.currentText().strip('(默认）')),
            'm_top': int(self.ui.comboBox_11.currentText().strip('（默认）')),
            'f_tip': self.ui.lineEdit_23.text().strip() or "0.14",
            'flatten': self.ui.comboBox_8.currentText() == "True",
            'attr': self.ui.comboBox_9.currentText()
        }

    def get_mosfet_params(self):
        """获取MOSFET参数"""
        # 构建属性列表
        attr = []
        if self.ui.checkBox.isChecked():
            attr.append('25')
            if self.ui.radioButton.isChecked():
                attr.append('ud')
            elif self.ui.radioButton_2.isChecked():
                attr.append('od')

        if self.ui.checkBox_2.isChecked() and self.ui.radioButton_3.isChecked():
            attr.append('na')

        if self.ui.checkBox_3.isChecked():
            attr.append('mac')

        vt_type = self.ui.comboBox_7.currentText()
        if vt_type in ['lvt', 'hvt']:
            attr.append(vt_type)

        # 解析体连接方式
        bulk_con = []
        bulk_con_text = self.ui.comboBox_6.currentText()
        if bulk_con_text == '0(S)':
            bulk_con = [0]
        elif bulk_con_text == '1(G)':
            bulk_con = [1]
        elif bulk_con_text == '2(D)':
            bulk_con = [2]

        return {
            'is_nmos': self.ui.radioButton_3.isChecked(),
            'is_pmos': self.ui.radioButton_4.isChecked(),
            'name': self.ui.lineEdit_11.text().strip(),
            'width': self.ui.lineEdit_12.text().strip(),
            'length': self.ui.lineEdit_13.text().strip(),
            'nf': self.ui.lineEdit_14.text().strip(),
            'spectre': self.ui.checkBox_4.isChecked(),
            'attr': attr,
            'pin_con_type': self.ui.comboBox_5.currentText(),
            'bulk_con': bulk_con
        }

    def get_netlist_path(self):
        """获取网表文件路径"""
        return self.ui.lineEditNetlist.text().strip()

    def get_tech_dir(self):
        """获取工艺文件目录"""
        return self.ui.lineEditTechDir.text().strip()

    def validate_number(self, value_str, field_name, value_type=float):
        """验证数字输入"""
        if not value_str:
            return None
        try:
            return value_type(value_str)
        except ValueError:
            return None

    def show_warning(self, title, message):
        """显示警告消息框"""
        QMessageBox.warning(self.ui, title, message)

    def show_error(self, title, message):
        """显示错误消息框"""
        QMessageBox.critical(self.ui, title, message)

    def show_info(self, title, message):
        """显示信息消息框"""
        QMessageBox.information(self.ui, title, message)

    def show_progress(self, show=True):
        """显示或隐藏进度条"""
        if show:
            self.progress_bar.show()
        else:
            self.progress_bar.hide()

    def update_progress(self, current, total):
        """更新进度条"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()

    def reset_progress(self):
        """重置进度条"""
        self.progress_bar.setValue(0)
        self.progress_bar.hide()