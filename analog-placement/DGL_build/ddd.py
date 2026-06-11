import dgl
import torch
from netlist.parse_netlist import parse_spice
from ckt.graph import build_graph
from init_feature import initFeature
import os


def cdl_to_dgl(cdl_file_path, save_path=None):
    """
    将CDL网表文件转换为DGL图并可选保存到文件

    Args:
        cdl_file_path: CDL网表文件的路径
        save_path: DGL图保存路径（.bin格式），如果为None则不保存

    Returns:
        G_dgl: 生成的DGL图对象
        topCkt: 解析后的电路对象
    """
    print(f"正在解析网表文件: {cdl_file_path}")

    # 1. 读取CDL文件内容（解决中文编码问题）
    try:
        with open(cdl_file_path, 'r', encoding='utf-8') as f:
            netlist_string = f.read()
    except UnicodeDecodeError:
        with open(cdl_file_path, 'r', encoding='gbk') as f:
            netlist_string = f.read()

    # 2. 解析SPICE网表
    netlist = parse_spice(netlist_string)
    print(f"网表解析完成，找到 {len(netlist)} 个子电路")

    # 3. 构建NetworkX多重有向图
    G_dict, topCkt = build_graph(netlist)
    G_nx = G_dict[topCkt.name]
    print(f"NetworkX图构建完成: 节点数={G_nx.number_of_nodes()}, 边数={G_nx.number_of_edges()}")

    # 4. 转换为DGL图并初始化特征
    G_dgl = initFeature(G_nx, topCkt)
    print(f"DGL图转换完成: 节点特征维度={G_dgl.ndata['feat'].shape}, 边特征维度={G_dgl.edata['type'].shape}")

    # 5. 保存DGL图到文件（如果指定了保存路径）
    if save_path:
        dgl.save_graphs(save_path, [G_dgl])
        print(f"DGL图已保存到: {save_path}")

    return G_dgl, topCkt


if __name__ == "__main__":
    # 在这里修改你的网表文件路径和保存路径
    CDL_FILE = "rec_nmos100.cdl"
    SAVE_FILE = "./rec_nmos100_dgl.bin"

    # 执行转换
    G_dgl, topCkt = cdl_to_dgl(CDL_FILE, SAVE_FILE)

    # 可选：打印DGL图的详细信息
    print("\n=== DGL图详细信息 ===")
    print(f"图类型: {type(G_dgl)}")
    print(f"节点数: {G_dgl.num_nodes()}")
    print(f"边数: {G_dgl.num_edges()}")
    print(f"节点特征列表: {list(G_dgl.ndata.keys())}")
    print(f"边特征列表: {list(G_dgl.edata.keys())}")