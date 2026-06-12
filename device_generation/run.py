import sys
import subprocess
import os
from PyQt5.QtWidgets import (
    QApplication, QVBoxLayout, QWidget, QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt
from device_generation.ui import CircuitUI
from device_generation.netlist_parser import NetlistParser
from device_generation.gds_generator import GDSGenerator

if hasattr(sys, '_MEIPASS'):
    sys.path.append(sys._MEIPASS)
else:
    sys.path.append(os.path.dirname(__file__))

class CircuitGenerator(QWidget):
    """电路生成器主类，整合所有模块"""

    def __init__(self):
        # 初始化各个模块
        super().__init__()
        self.ui = CircuitUI()
        layout = QVBoxLayout(self)
        layout.addWidget(self.ui)
        layout.setContentsMargins(0, 0, 0, 0)
        # 新增：布局上下间距，让按钮和主体区分开
        layout.setSpacing(10)

        # ===================== 【修改】只保留 GDS 目录变量，移除文件/批量标记 =====================
        self.last_gds_dir = ""   # 记录最后一次 GDS 保存目录
        # 按钮文字改为更直观的描述
        self.open_klayout_btn = QPushButton("打开 GDS 保存文件夹")
        self.open_klayout_btn.setMinimumHeight(35)
        self.open_klayout_btn.setEnabled(False)  # 初始禁用，生成GDS后才可用
        self.open_klayout_btn.clicked.connect(self.open_gds_folder)
        layout.addWidget(self.open_klayout_btn)
        # =================================================================

        self.parser = NetlistParser()
        self.generator = GDSGenerator()
        self.connect_ui_events()

    def connect_ui_events(self):
        # 定义处理函数字典
        handlers = {
            'generate_component': self.handle_generate_component,
            'generate_capacitor': self.handle_generate_capacitor,
            'generate_mosfet': self.handle_generate_mosfet,
            'generate_from_netlist': self.handle_generate_from_netlist
        }
        self.ui.connect_signals(handlers)

    # ===================== 【重写】核心函数：打开GDS文件夹 =====================
    def open_gds_folder(self):
        """WSL专用稳定打开文件夹方案，用wslpath转换Windows路径"""
        if not self.last_gds_dir or not os.path.isdir(self.last_gds_dir):
            QMessageBox.warning(self, "提示", "暂无GDS目录，请先生成 GDS 文件！")
            return

        try:
            # 调用wslpath把Linux路径转为Windows可识别完整路径
            result = subprocess.check_output(
                ["wslpath", "-w", self.last_gds_dir],
                text=True
            )
            win_dir = result.strip()

            # 用explorer打开转换后的标准Windows路径
            subprocess.Popen(["explorer.exe", win_dir])
            QMessageBox.information(self, "成功", f"已打开GDS目录：\n{self.last_gds_dir}")

        except subprocess.CalledProcessError:
            # 兜底：唤起WSL内部Linux文件管理器
            subprocess.Popen(["xdg-open", self.last_gds_dir])
            QMessageBox.information(self, "提示", "Windows路径转换失败，已打开WSL本地文件夹")
        except Exception as e:
            QMessageBox.critical(self, "打开失败", f"错误详情：{str(e)}")
    # =================================================================

    def handle_generate_component(self):
        """处理生成组件按钮点击"""
        component_type = self.ui.ui.comboBox.currentText()
        if component_type == "电阻":
            self.handle_generate_resistor()
        elif component_type == "电容":
            self.handle_generate_capacitor()
        elif component_type == "MOS":
            self.handle_generate_mosfet()

    def handle_generate_resistor(self):
        """处理生成电阻"""
        params = self.ui.get_resistor_params()

        if not params['name']:
            self.ui.show_warning("输入错误", "请填写元件名称（name）")
            return

        try:
            width = self.ui.validate_number(params['width'], "宽度")
            length = self.ui.validate_number(params['length'], "长度")
            segments = self.ui.validate_number(params['segments'], "段数", int)

            def is_grid_aligned(value):
                value = round(value * 1000)
                return value % 5 == 0

            if width < 0.05:
                self.ui.show_warning("参数错误", "宽度（width）必须大于等于0.05um，请重新输入！")
                return
            if not is_grid_aligned(width):
                self.ui.show_warning("参数错误", "宽度（width）必须为最小网格单位0.005um整数倍，请重新输入！")
                return
            if length < 0.05:
                self.ui.show_warning("参数错误", "长度（length）必须大于等于0.05um，请重新输入！")
                return
            if not is_grid_aligned(length):
                self.ui.show_warning("参数错误", "长度（length）必须为最小网格单位0.005um整数倍，请重新输入！")
                return

            if width is None or length is None or segments is None:
                self.ui.show_warning("输入错误", "请填写有效的数值参数！")
                return

            seg_space = float(params['seg_space'])
            if seg_space  < 0.1:
                self.ui.show_warning("参数错误", "seg_space 必须大于等于0.1um，请重新输入！")
                return
            if not is_grid_aligned(seg_space):
                self.ui.show_warning("参数错误", "段间距(seg_space)必须为最小网格单位0.005um整数倍，请重新输入！")
                return

            # 生成电阻
            success, result = self.generator.generate_resistor({
                'name': params['name'],
                'series': params['series'],
                'w': width,
                'l': length,
                'seg_num': segments,
                'seg_space': seg_space,
                'attr': params['attr']
            })

            if success:
                self.ui.show_info("成功", f"电阻GDS文件已生成：{result}")
                # ===================== 【修改】提取文件所在目录 =====================
                self.last_gds_dir = os.path.dirname(result)
                self.open_klayout_btn.setEnabled(True)
                # =================================================================
            else:
                self.ui.show_error("生成失败", f"生成过程出错：{result}")

        except ValueError as e:
            self.ui.show_warning("输入格式错误", f"参数格式错误：{str(e)}")
        except Exception as e:
            self.ui.show_error("生成失败", f"生成过程出错：{str(e)}")

    def handle_generate_capacitor(self):
        """处理生成电容"""
        params = self.ui.get_capacitor_params()

        # 验证输入
        if not params['name']:
            self.ui.show_warning("输入错误", "请填写电容名称（name）")
            return

        try:
            width = self.ui.validate_number(params['width'], "宽度")
            length = self.ui.validate_number(params['length'], "长度")
            spacing = self.ui.validate_number(params['spacing'], "间距")
            nf = self.ui.validate_number(params['nf'], "指数量", int)
            f_tip = self.ui.validate_number(params['f_tip'], "指端长度")

            if None in [width, length, spacing, nf]:
                self.ui.show_warning("输入错误", "请填写有效的数值参数！")
                return

            # ===================== 1. 定义TSMC40完整金属层规则 =====================
            METAL_RULES = {
                1: {'min_w': 0.1, 'min_sp': 0.15},
                2: {'min_w': 0.1, 'min_sp': 0.15},
                3: {'min_w': 0.1, 'min_sp': 0.15},
                4: {'min_w': 0.1, 'min_sp': 0.15},
                5: {'min_w': 0.44, 'min_sp': 0.46},
                6: {'min_w': 0.44, 'min_sp': 0.46}
            }
            GRID = 0.005
            EPS = 1e-6

            # ===================== 2. 基础参数校验 =====================
            # 指数量最小值校验
            if nf < 2:
                self.ui.show_warning("参数错误", "指数量(nf)最小为2！")
                return

            # 金属层范围校验
            m_bot = params['m_bot']
            m_top = params['m_top']
            if m_top <= m_bot:
                self.ui.show_warning("参数错误", "m_top必须大于m_bot，请重新选择！")
                return

            if m_top - m_bot + 1 != int(params['attr'][0]):
                self.ui.show_warning("参数错误", "金属层数不匹配，请重新选择！")
                return


            # ===================== 3. 自动计算最严格的规则 =====================
            # 找出选择的金属层中最大的最小宽度和最小间距
            max_min_w = 0.0
            max_min_sp = 0.0
            for layer in range(m_bot, m_top + 1):
                if METAL_RULES[layer]['min_w'] > max_min_w:
                    max_min_w = METAL_RULES[layer]['min_w']
                if METAL_RULES[layer]['min_sp'] > max_min_sp:
                    max_min_sp = METAL_RULES[layer]['min_sp']

            # 自动设置f_tip默认值（根据最严格的间距）
            if f_tip is None:
                f_tip = 0.14

            # ===================== 4. 统一参数校验（消除重复代码） =====================
            # 网格对齐校验函数
            # ✅ 100%准确，无任何精度问题
            def Ris_grid_aligned(value):
                # 1μm = 1000nm，TSMC40网格=5nm
                value= round(value * 1000)
                return value % 5 == 0

            # 宽度校验
            if width < max_min_w:
                self.ui.show_warning("参数错误",
                                     f"选择的金属层范围M{m_bot}-M{m_top}，最小宽度为{max_min_w}um！")
                return
            if not Ris_grid_aligned(width):
                self.ui.show_warning("参数错误", "宽度必须为0.005um的整数倍！")
                return

            # 长度校验
            if length < 0.1:
                self.ui.show_warning("参数错误", "长度必须大于0.1um！")
                return
            if not Ris_grid_aligned(length):
                self.ui.show_warning("参数错误", "长度必须为0.005um的整数倍！")
                return

            # 间距校验
            if spacing < max_min_sp:
                self.ui.show_warning("参数错误",
                                     f"选择的金属层范围M{m_bot}-M{m_top}，最小间距为{max_min_sp}um！")
                return
            if not Ris_grid_aligned(spacing):
                self.ui.show_warning("参数错误", "间距必须为0.005um的整数倍！")
                return

            # 指端长度校验
            if f_tip < max_min_sp:
                self.ui.show_warning("参数错误",
                                     f"指端长度最小为{max_min_sp}um！")
                return
            if not Ris_grid_aligned(f_tip):
                self.ui.show_warning("参数错误", "指端长度必须为0.005um的整数倍！")
                return

            # ===================== 5. 生成电容 =====================
            success, result = self.generator.generate_capacitor({
                'name': params['name'],
                'w': width,
                'l': length,
                'sp': spacing,
                'nf': nf,
                'm_bot': m_bot,
                'm_top': m_top,
                'attr': params['attr'],
                'f_tip': f_tip,
                'flatten': params['flatten']
            })

            if success:
                self.ui.show_info("成功", f"电容GDS文件已生成：{result}")
                # ===================== 【修改】提取文件所在目录 =====================
                self.last_gds_dir = os.path.dirname(result)
                self.open_klayout_btn.setEnabled(True)
                # =================================================================
            else:
                self.ui.show_error("生成失败", f"生成过程出错：{result}")

        except ValueError as e:
            self.ui.show_warning("输入格式错误", f"参数格式错误：{str(e)}")
        except Exception as e:
            self.ui.show_error("生成失败", f"生成过程出错：{str(e)}")

    def handle_generate_mosfet(self):
        """处理生成MOSFET"""
        params = self.ui.get_mosfet_params()

        # 验证MOS类型
        if not (params['is_nmos'] or params['is_pmos']):
            self.ui.show_warning("输入错误", "请选择MOS类型（NMOS/PMOS）")
            return

        # 验证名称
        if not params['name']:
            self.ui.show_warning("输入错误", "请填写MOS名称（name）")
            return

        try:
            width = self.ui.validate_number(params['width'], "宽度")
            length = self.ui.validate_number(params['length'], "长度")
            nf = self.ui.validate_number(params['nf'], "指数量", int)
            def Nis_grid_aligned(value):
                # 1μm = 1000nm，TSMC40网格=5nm
                value= round(value * 1000)
                return value % 5 == 0

            if None in [width, length, nf]:
                self.ui.show_warning("输入错误", "请填写有效的数值参数！")
                return

            if not Nis_grid_aligned(width):
                self.ui.show_warning("参数错误", "宽度必须为0.005um的整数倍！")
                return


            if not Nis_grid_aligned(length):
                self.ui.show_warning("参数错误", "长度必须为0.005um的整数倍！")
                return
            if length < 0.04:
                self.ui.show_warning("输入错误", f"栅长不能小于0.04μm！")
                return


            if params['spectre']:
                single_finger_w = width / nf
            else:
                single_finger_w = width

            if single_finger_w < 0.05:
                self.ui.show_warning("输入错误", f"单指宽度不能小于0.05μm！当前单指宽度为{single_finger_w:.3f}μm")
                return

            # 解析引脚连接类型
            pin_con_type = params['pin_con_type']
            if pin_con_type == "None":
                pin_con_type = None

            # 生成MOSFET
            success, result = self.generator.generate_mosfet({
                'name': params['name'],
                'nch': params['is_nmos'],
                'w': width,
                'l': length,
                'nf': nf,
                'attr': params['attr'],
                'spectre': params['spectre'],
                'pinConType': pin_con_type,
                'bulk_con': params['bulk_con']
            })

            if success:
                self.ui.show_info("成功", f"MOS管GDS文件已生成：{result}")
                # ===================== 【修改】提取文件所在目录 =====================
                self.last_gds_dir = os.path.dirname(result)
                self.open_klayout_btn.setEnabled(True)
                # =================================================================
            else:
                self.ui.show_error("生成失败", f"生成过程出错：{result}")

        except ValueError as e:
            self.ui.show_warning("输入格式错误", f"参数格式错误：{str(e)}")
        except Exception as e:
            self.ui.show_error("生成失败", f"生成过程出错：{str(e)}")

    def handle_generate_from_netlist(self):
        """处理从网表生成（批量GDS）"""
        netlist_path = self.ui.get_netlist_path()

        if not netlist_path:
            self.ui.show_warning("输入错误", "请选择网表文件！")
            return

        # 设置输出目录
        output_dir = os.path.join(os.path.dirname(netlist_path), "gds")
        self.generator.set_output_dir(output_dir)

        try:
            # 解析网表
            devices = self.parser.parse_netlist(netlist_path)

            # 计算总器件数
            total_devices = len(devices["resistors"]) + len(devices["capacitors"]) + len(devices["mosfets"])

            if total_devices == 0:
                self.ui.show_info("提示", "网表中未解析到电阻、电容或MOS管！")
                return

            # 显示并初始化进度条
            self.ui.show_progress(True)
            self.ui.update_progress(0, total_devices)

            # 使用进度回调生成器件
            base_name = os.path.splitext(os.path.basename(netlist_path))[0]

            # 传递进度回调函数给生成器
            def progress_callback(current, total):
                self.ui.update_progress(current, total)

            results = self.generator.generate_from_netlist_data(
                devices,
                base_name,
                progress_callback=progress_callback
            )

            # 显示结果
            result_message = f"共生成{results['success']}个器件GDS文件：\n"
            result_message += f"电阻：{len(devices['resistors'])}个（成功{results['success']}个，失败{results['failed']}个）\n"

            result_message += f"电容：{len(devices['capacitors'])}个\n"
            result_message += f"MOS管：{len(devices['mosfets'])}个\n"
            result_message += f"文件存储路径：{results['output_dir']}"

            self.ui.show_info("生成完成", result_message)

            # ===================== 【修改】直接赋值目录 =====================
            self.last_gds_dir = results['output_dir']
            self.open_klayout_btn.setEnabled(True)
            # =================================================================

            # 如果有失败项，显示详细信息
            if results['failed'] > 0:
                details = "\n".join([d for d in results['details'] if d.startswith("✗")])
                self.ui.show_warning("部分失败", f"以下器件生成失败：\n{details}")

        except Exception as e:
            self.ui.show_error("生成失败", f"生成过程出错：{str(e)}")
        finally:
            # 重置进度条
            self.ui.reset_progress()