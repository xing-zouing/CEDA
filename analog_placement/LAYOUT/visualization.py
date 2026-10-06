import matplotlib
import sys

# 自动检测当前运行的后端，避免冲突
if 'PyQt5' in sys.modules or 'PyQt6' in sys.modules:
    matplotlib.use('Qt5Agg')
else:
    matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def draw_layout_on(ax, x, y, devices, sym_pairs, x_sym, title="Layout of Devices",
                   show_legend=True):
    """把设备布局画到给定的 Axes 上，显示设备、对称轴和重叠区域。

    与 plot_layout 的区别是这里不创建 figure、也不弹窗，
    方便嵌入到 Qt 界面里的内嵌画布上。

    show_legend=False 时不画图例，交给调用方统一放一个（左右并排两幅图时用）。
    """
    for i, dev in enumerate(devices):
        xi, yi = x[i], y[i]
        wi, hi = dev['width'], dev['height']
        rect = patches.Rectangle(
            (xi - wi / 2, yi - hi / 2), wi, hi, linewidth=1, edgecolor='blue', facecolor='none',
            label='Devices' if i == 0 else None
        )
        ax.add_patch(rect)
        # ax.text(xi + 0.1, yi, dev['name'], fontsize=8, color='black')
    for i in range(len(devices)):
        for j in range(i + 1, len(devices)):
            xi, yi = x[i], y[i]
            xj, yj = x[j], y[j]
            wi, hi = devices[i]['width'], devices[i]['height']
            wj, hj = devices[j]['width'], devices[j]['height']
            left_i, right_i = xi - wi / 2, xi + wi / 2
            bottom_i, top_i = yi - hi / 2, yi + hi / 2
            left_j, right_j = xj - wj / 2, xj + wj / 2
            bottom_j, top_j = yj - hj / 2, yj + hj / 2
            overlap_width = min(right_i, right_j) - max(left_i, left_j)
            overlap_height = min(top_i, top_j) - max(bottom_i, bottom_j)
            if overlap_width > 0 and overlap_height > 0:
                overlap_left = max(left_i, left_j)
                overlap_bottom = max(bottom_i, bottom_j)
                rect = patches.Rectangle(
                    (overlap_left, overlap_bottom), overlap_width, overlap_height,
                    linewidth=0, facecolor='yellow', alpha=0.5, label='Overlap' if i == 0 and j == 1 else None
                )
                ax.add_patch(rect)
    y_min = min(y) - max(dev['height'] / 2 for dev in devices) - 1
    y_max = max(y) + max(dev['height'] / 2 for dev in devices) + 1
    x_min = min(x) - max(dev['width'] / 2 for dev in devices) - 1
    x_max = max(x) + max(dev['width'] / 2 for dev in devices) + 1
    ax.axvline(x=x_sym, color='green', linestyle='--', label='Symmetry Axis')
    ax.set_xlabel('X Coordinate')
    ax.set_ylabel('Y Coordinate')
    ax.set_title(title)
    if show_legend:
        ax.legend()
    ax.set_aspect('equal')
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    # 原实现在结尾是 ax.grid(True) 之后又 plt.grid(False)，净效果为不显示网格，
    # 这里直接不画网格，保持和原来完全一样的观感


def plot_layout(x, y, devices, sym_pairs, x_sym, title="Layout of Devices"):
    """在独立的 matplotlib 窗口中显示布局（保持原有行为，供 test.py 等沿用）"""
    fig, ax = plt.subplots(figsize=(10, 10))
    draw_layout_on(ax, x, y, devices, sym_pairs, x_sym, title)
    plt.show()