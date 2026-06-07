import gdspy

# 创建一个简单的矩形cell
cell = gdspy.Cell("TEST_RES")
# 画一个1μm×10μm的矩形（模拟电阻的版图），layer设为1（GDSII支持0-255）
res_poly = gdspy.Polygon(
    [(0, 0), (0.6, 0), (0.6, 10), (0, 10)],  # 对应网表中wr=600e-9（0.6μm）、lr=10e-6（10μm）
    layer=1
)
cell.add(res_poly)

# 生成测试GDS
gdspy.write_gds(
    "test_valid.gds",
    [cell],
    unit=1.0e-6,  # 用户单位：1μm
    precision=1.0e-9  # 最小精度：1nm
)
print("测试GDS生成完成")