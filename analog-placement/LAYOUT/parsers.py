import re

def parse_spice_value(value):
    """解析 SPICE 参数值，处理单位转换为浮点数（单位：微米）。"""
    units = {'f': 1e-15, 'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'm': 1e-3, 'k': 1e3, 'meg': 1e6}
    match = re.match(r'([0-9\.]+)([a-zA-Z]*)', value)
    if match:
        num = float(match.group(1))
        unit = match.group(2).lower()
        if unit in units:
            return num * units[unit] / 1e-6  # 转换为微米
        return num / 1e-6
    raise ValueError(f"无效的 SPICE 值：{value}")

def longest_common_prefix_ending_with(strs, char='_'):
    """计算字符串列表的最长公共前缀，以指定字符结尾。"""
    if not strs:
        return ""
    P = strs[0]
    candidates = [i for i in range(len(P)) if P[i] == char]
    if not candidates:
        return ""
    max_i = max([i for i in candidates if all(s[:i + 1] == P[:i + 1] for s in strs)], default=-1)
    if max_i != -1:
        return P[:max_i + 1]
    else:
        return ""

def parse_spice_netlist(file_path):
    """解析 SPICE 网表，提取设备尺寸、连接信息、设备索引映射和逻辑组，处理 multi 参数生成多个实例。"""
    devices = []
    node_to_devices = {}
    device_name_to_index = {}
    logical_groups = {}  # 存储逻辑组，例如 {'M0': [M0_0_idx, M1_1_idx], 'M1': [M1_0_idx, M1_1_idx]}
    index = 0

    with open(file_path, 'r') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if line.startswith('M') or line.startswith('C') or line.startswith('R'):
            parts = line.split()
            instance_name = parts[0]

            # 提取节点
            if line.startswith('M'):
                nodes = parts[1:5]  # 晶体管：漏极、栅极、源极、衬底
            else:  # 'C' 或 'R'
                nodes = parts[1:3]  # 电容/电阻：正、负节点

            # 提取参数
            params = {}
            param_start = 5 if line.startswith('M') else 3
            for param in parts[param_start:]:
                if '=' in param:
                    key, value = param.split('=')
                    params[key.strip()] = value.strip()

            # 处理设备尺寸
            if line.startswith('M'):
                if 'w' in params and 'l' in params:
                    w = parse_spice_value(params['w'])
                    l = parse_spice_value(params['l'])
                    multi = int(params.get('multi', '1'))
                    base_name = instance_name
                    group_indices = []
                    for m in range(multi):
                        unique_instance_name = f"{instance_name}_{m}" if multi > 1 else instance_name
                        devices.append({'name': unique_instance_name, 'width': w, 'height': l})
                        device_name_to_index[unique_instance_name] = index
                        group_indices.append(index)
                        for node in nodes:
                            if node not in node_to_devices:
                                node_to_devices[node] = []
                            node_to_devices[node].append(index)
                        index += 1
                    if multi > 1:
                        logical_groups[base_name] = group_indices
                else:
                    print(f"警告：晶体管 {instance_name} 缺少 'w' 或 'l' 参数")
                    continue
            elif line.startswith('C') or line.startswith('R'):
                if 'w' in params and 'l' in params:
                    w = parse_spice_value(params['w'])
                    l = parse_spice_value(params['l'])
                    devices.append({'name': instance_name, 'width': w, 'height': l})
                    device_name_to_index[instance_name] = index
                    for node in nodes:
                        if node not in node_to_devices:
                            node_to_devices[node] = []
                        node_to_devices[node].append(index)
                    index += 1
                else:
                    print(f"警告：元件 {instance_name} 缺少 'w' 或 'l' 参数")
                    continue

    nets = [node_to_devices[node] for node in node_to_devices if len(node_to_devices[node]) > 1]
    return devices, nets, device_name_to_index, logical_groups

def parse_sym_file(file_path, device_name_to_index):
    """解析对称文件，返回对称对和配对共质心组，处理前缀和 multi 实例。"""
    sym_pairs = []
    cc_pairs = []  # 存储配对的共质心组，例如 [(group1, group2), ...]

    all_names = set()
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            names = line.split()
            all_names.update(names)
    all_names = list(all_names)

    # 计算以 '_' 结尾的最长公共前缀
    prefix = longest_common_prefix_ending_with(all_names)

    # 处理每行
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            # 移除前缀
            parts = [name[len(prefix):] for name in parts]
            if len(parts) == 2:  # 对称对
                dev1, dev2 = parts
                indices1 = [idx for name, idx in device_name_to_index.items() if
                            name == dev1 or name.startswith(dev1 + '_')]
                indices2 = [idx for name, idx in device_name_to_index.items() if
                            name == dev2 or name.startswith(dev2 + '_')]
                if indices1 and indices2:
                    if len(indices1) == len(indices2):
                        for idx1, idx2 in zip(indices1, indices2):
                            sym_pairs.append((idx1, idx2))
                        if len(indices1) > 1:
                            cc_pairs.append((indices1, indices2))
                    else:
                        print(f"警告：对称对 {dev1}, {dev2} 的 multi 实例数量不匹配")
                else:
                    print(f"警告：对称对 {dev1}, {dev2} 未在网表中找到")
            elif len(parts) == 1:  # 自对称设备
                dev = parts[0]
                indices = [idx for name, idx in device_name_to_index.items() if
                           name == dev or name.startswith(dev + '_')]
                if indices:
                    if len(indices) == 1:
                        sym_pairs.append((indices[0], indices[0]))  # 单设备自对称
                    # 对于 multi > 1，不做处理
                else:
                    print(f"警告：自对称设备 {dev} 未在网表中找到")

    return sym_pairs, cc_pairs