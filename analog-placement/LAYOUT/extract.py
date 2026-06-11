import dgl
import os
import numpy as np
import time

def find_nodes(node_1, node_2,types,src_nodes,dst_nodes):
    num_edges1 = 0 # 例如节点1->节点2的边条数
    edges_index1 = [] # 例如节点1->节点2的索引
    edges_types1 = [] # 例如节点1->节点2的边类型列表
    for k1 in range(len(types)):
        if src_nodes[k1] == node_1 and dst_nodes[k1] == node_2:
            num_edges1 += 1
            edges_index1.append(k1)
            edges_types1.append(types[k1])
    num_edges2 = 0 # 例如节点2->节点1的边条数
    edges_index2 = [] # 例如节点2->节点1的索引
    edges_types2 = []  # 例如节点2->节点1的边类型列表
    for k2 in range(len(types)):
        if src_nodes[k2] == node_2 and dst_nodes[k2] == node_1:
            num_edges2 += 1
            edges_index2.append(k2)
            edges_types2.append(types[k2])
    return num_edges1, num_edges2, edges_index1, edges_index2, edges_types1, edges_types2

def rmv_last(string):
    if string[-1] == '/':
        return string[:-1]
    else:
        return string


def add_match_comment_unified_group(sym_file, sp_file, output_file):
    """
    将.sym中所有器件统一归入一个group，注释格式：
    ****dev1 match with dev2, group1(所有器件用\连接)
    """
    all_devices = []  # 收集所有器件名（按出现顺序）
    pair_map = {}     # 器件 -> 配对注释（不含group部分）

    with open(sym_file, 'r', encoding='utf-8') as f:
        for line in f:
            names = line.strip().split()
            if len(names) == 2:
                dev1, dev2 = names
                all_devices.append(dev1)
                all_devices.append(dev2)
                # 为两个器件建立配对字符串（不包含group）
                pair_str = f"{dev1} match with {dev2}"
                pair_map[dev1] = pair_str
                pair_map[dev2] = pair_str

    # 去重但保持顺序（如果.sym无重复，可省略）
    seen = set()
    unique_devices = []
    for d in all_devices:
        if d not in seen:
            unique_devices.append(d)
            seen.add(d)

    # 构建统一 group 字符串
    group_content = "\\".join(unique_devices)
    group_str = f"group1({group_content})"

    # 读取.sp文件
    with open(sp_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    output_lines = []
    for line in lines:
        stripped = line.rstrip('\n')

        if not line.strip() or line.strip().startswith('*'):
            output_lines.append(line)
            continue

        first_word = line.strip().split()[0] if line.strip() else ""

        if first_word in pair_map:
            # 构造完整注释：****配对描述, group1(所有器件)
            comment = f"****{pair_map[first_word]}, {group_str}"
            new_line = stripped + "     " + comment + "\n"
            output_lines.append(new_line)
        else:
            output_lines.append(line)

    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)

    print(f"✅ 统一组模式处理完成！结果已保存至：{output_file}")
    print(f"👥 组内器件：{', '.join(unique_devices)}")

def constraint_extraction():
    start_time = time.time()
    graphs, _ = dgl.load_graphs('./netlists/CD2101_250710/rec_nmos100.dgl')
    graph = graphs[0]
    netlist_name = (''.join(chr(num) for num in graph.ndata['name'][0].tolist()).split('/')[0])

    # 去除名称字符串的最后一位/符号

    # 获取图中所有节点的名称
    nodes_name = []  # 节点名称列表
    for k in range(graph.number_of_nodes()):
        # print(''.join(chr(num) for num in graph.ndata['name'][k].tolist()))
        nodes_name.append(rmv_last(''.join(chr(num) for num in graph.ndata['name'][k].tolist())).split('/')[1])

    # 图匹配的前处理（根据当前图的节点类型和节点特征判断节点对之间是否存在匹配的可能），过滤（滤波）
    possible_match = []  # 可能的匹配对
    match_pairs = []  # 匹配对
    mismatch_pairs = []  # 非匹配对
    matchs = dict()
    mismatchs = dict()
    types = graph.edata['type'].tolist()  # 图节点类型列表
    src_nodes = graph.edges()[0].tolist()  # 源节点序号列表
    dst_nodes = graph.edges()[1].tolist()  # 目标节点序号列表

    # 遍历图中的节点
    for i in range(graph.number_of_nodes()):
        for j in range(i + 1, graph.number_of_nodes()):
            # 比较两个节点类型和属性是否相等
            if (graph.ndata['label'][i].tolist() == graph.ndata['label'][j].tolist() and graph.ndata['feat'][
                i].tolist() == graph.ndata['feat'][j].tolist()):
                possible_match.append((
                                      rmv_last(''.join(chr(num) for num in graph.ndata['name'][i].tolist())).split('/')[
                                          1],
                                      rmv_last(''.join(chr(num) for num in graph.ndata['name'][j].tolist())).split('/')[
                                          1]))
                # # 比较两个节点之间是否存在连接
                # if graph.has_edges_between(i, j):
                #     match_pairs.append((rmv_last(''.join(chr(num) for num in graph.ndata['name'][i].tolist())).split('/')[1],rmv_last(''.join(chr(num) for num in graph.ndata['name'][j].tolist())).split('/')[1]))
                # else:
                #     mismatch_pairs.append((rmv_last(''.join(chr(num) for num in graph.ndata['name'][i].tolist())).split('/')[1], rmv_last(''.join(chr(num) for num in graph.ndata['name'][j].tolist())).split('/')[1]))

                # 两个节点间的边连接数大于1，且对应边列表的值相等(需要修改)
                num_edges1_1, num_edges2_1, edges_index1_1, edges_index2_1, edges_types1_1, edges_types2_1 = find_nodes(
                    i, j,types,src_nodes,dst_nodes)
                count = sum(x == y for x, y in zip(edges_types1_1, edges_types2_1))
                if num_edges1_1 > 1 and count > 1:
                    match_pairs.append((rmv_last(''.join(chr(num) for num in graph.ndata['name'][i].tolist())).split(
                        '/')[1], rmv_last(''.join(chr(num) for num in graph.ndata['name'][j].tolist())).split('/')[1]))
                else:
                    mismatch_pairs.append((rmv_last(''.join(chr(num) for num in graph.ndata['name'][i].tolist())).split(
                        '/')[1], rmv_last(''.join(chr(num) for num in graph.ndata['name'][j].tolist())).split('/')[1]))

            else:
                mismatch_pairs.append((
                                      rmv_last(''.join(chr(num) for num in graph.ndata['name'][i].tolist())).split('/')[
                                          1],
                                      rmv_last(''.join(chr(num) for num in graph.ndata['name'][j].tolist())).split('/')[
                                          1]))

    matchs[netlist_name] = match_pairs
    mismatchs[netlist_name] = mismatch_pairs

    # print(matchs)
    # print('可能匹配对', len(possible_match), possible_match)

    # print('匹配器件对：', match_pairs)
    print('匹配约束提取时间', time.time() - start_time, 's')

    # 过滤掉包含'C'或'R'的元素
    filtered_list = [
        item for item in match_pairs
        if not any('R' in elem or 'C' in elem for elem in item)
    ]
    print('匹配器件对：', filtered_list)

    # 打开文件以写入模式
    # with open('./LDO.sym', 'w') as file:
    with open('./' + netlist_name + '.sym', 'w') as file:
        # 遍历列表中的每个元组
        # for item in match_pairs:
        for item in filtered_list:
            # 将元组中的元素用空格连接成字符串，并添加换行符
            line = ' '.join(item) + '\n'
            # 将处理后的字符串写入文件
            file.write(line)

    # 网表、匹配结果融合

    add_match_comment_unified_group('./' + netlist_name + '.sym', './netlists/CD2101_250710/' + netlist_name + '.cdl',
                                    './new_' + netlist_name + '.cdl')
    current_dir_os = os.path.dirname(os.path.abspath(__file__))
    outpath= current_dir_os +"\\"+'new_' + netlist_name + '.cdl'

    return outpath


if __name__ == "__main__":
    print(constraint_extraction())
