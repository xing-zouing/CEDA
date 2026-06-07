import re


class NetlistParser:
    """网表文件解析器"""

    @staticmethod
    def parse_netlist(netlist_path):
        """解析网表文件，提取电阻、电容、MOS管参数"""
        devices = {
            "resistors": [],  # 电阻列表
            "capacitors": [],  # 电容列表
            "mosfets": []  # MOS管列表
        }

        current_subckt = ""

        # 正则表达式匹配各器件
        subckt_pattern = re.compile(r"\.subckt\s+(\w+)\s+.*")
        res_pattern = re.compile(
            r"^(x\w+)\s+.*\s+rppolywo_m\s+lr=([\d.e-]+)\s+wr=([\d.e-]+)\s+.*series=(\d+)\s+segspace=([\d.e-]+)"
        )
        mos_pattern = re.compile(
            r"^(x\w+)\s+.*\s+(nch|pch)_(\w+)_mac\s+l=([\d.e-]+)\s+w=([\d.e-]+)\s+.*nf=(\d+)"
        )
        cap_pattern = re.compile(
            r"^(xc\w+)\s+.*\s+cfmom_2t\s+nr=(\d+)\s+lr=([\d.e-]+)\s+w=([\d.e-]+)\s+s=([\d.e-]+)\s+stm=(\d+)\s+spm=(\d+)\s+.*ftip=([\d.e-]+)"
        )

        try:
            with open(netlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("**"):
                        continue

                    # 1. 更新当前子电路名
                    subckt_match = subckt_pattern.match(line)
                    if subckt_match:
                        current_subckt = subckt_match.group(1)
                        continue

                    # 2. 解析电阻
                    res_match = res_pattern.match(line)
                    if res_match:
                        devices = NetlistParser._parse_resistor(res_match, current_subckt, devices)
                        continue

                    # 3. 解析MOS管
                    mos_match = mos_pattern.match(line)
                    if mos_match:
                        devices = NetlistParser._parse_mosfet(mos_match, current_subckt, devices)
                        continue

                    # 4. 解析电容
                    cap_match = cap_pattern.match(line)
                    if cap_match:
                        devices = NetlistParser._parse_capacitor(cap_match, current_subckt, devices)
                        continue

        except FileNotFoundError:
            raise Exception(f"网表文件不存在: {netlist_path}")
        except Exception as e:
            raise Exception(f"解析网表文件出错: {str(e)}")

        return devices

    @staticmethod
    def _parse_resistor(res_match, current_subckt, devices):
        """解析电阻行"""
        inst_name = res_match.group(1)
        lr_m = float(res_match.group(2))  # 长度（米）
        wr_m = float(res_match.group(3))  # 宽度（米）
        series = int(res_match.group(4))  # 段数
        segspace_m = float(res_match.group(5))  # 段间距（米）

        # 单位转换：米 → 微米（×1e6）
        lr_um = lr_m * 1e6
        wr_um = wr_m * 1e6
        segspace_um = segspace_m * 1e6

        devices["resistors"].append({
            "subckt": current_subckt,
            "inst_name": inst_name,
            "l": lr_um,
            "w": wr_um,
            "series": True,
            "seg_num": series,
            "seg_space": segspace_um,
            "attr": ["wo", "m"]
        })

        return devices

    @staticmethod
    def _parse_mosfet(mos_match, current_subckt, devices):
        """解析MOS管行"""
        inst_name = mos_match.group(1)
        mos_type = mos_match.group(2)  # nch/pch
        vt_type = mos_match.group(3)  # lvt/hvt
        l_m = float(mos_match.group(4))
        w_m = float(mos_match.group(5))
        nf = int(mos_match.group(6))

        # 单位转换
        l_um = l_m * 1e6
        w_um = w_m * 1e6

        # 构建属性列表
        attr = [vt_type, "mac"]
        nch = True if mos_type == "nch" else False
        bulk_con = [0]

        devices["mosfets"].append({
            "subckt": current_subckt,
            "inst_name": inst_name,
            "nch": nch,
            "l": l_um,
            "w": w_um,
            "nf": nf,
            "attr": attr,
            "spectre": True,
            "pinConType": None,
            "bulkCon": bulk_con
        })

        return devices

    @staticmethod
    def _parse_capacitor(cap_match, current_subckt, devices):
        """解析电容行"""
        inst_name = cap_match.group(1)
        nr = int(cap_match.group(2))  # 指数量
        lr_m = float(cap_match.group(3))  # 长度（米）
        w_m = float(cap_match.group(4))  # 宽度（米）
        s_m = float(cap_match.group(5))  # 间距（米）
        stm = int(cap_match.group(6))  # 底层金属
        spm = int(cap_match.group(7))  # 顶层金属
        ftip_m = float(cap_match.group(8))  # 指端长度（米）

        # 单位转换
        lr_um = lr_m * 1e6
        w_um = w_m * 1e6
        s_um = s_m * 1e6
        ftip_um = ftip_m * 1e6

        devices["capacitors"].append({
            "subckt": current_subckt,
            "inst_name": inst_name,
            "l": lr_um,
            "w": w_um,
            "sp": s_um,
            "nf": nr,
            "m_bot": stm,
            "m_top": spm,
            "f_tip": ftip_um,
            "attr": ["2t"],
            "flatten": True
        })

        return devices