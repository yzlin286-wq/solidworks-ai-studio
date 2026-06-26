import os
import sys

# 添加vendored脚本路径到Python导入路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENDOR_SCRIPTS = os.path.join(SCRIPT_DIR, r"..\vendor\skills\solidworks-automation\scripts")
sys.path.insert(0, os.path.abspath(VENDOR_SCRIPTS))

from sw_connect import connect_solidworks, new_document, save_document, mm
from sw_part import start_sketch, end_sketch, sketch_rectangle, extrude_boss, sketch_circle, extrude_cut, chamfer
from sw_export import export_to_step

def main():
    # 配置输出路径
    OUTPUT_DIR = r"C:\Users\Vision\Documents\sw skill 应用化\outputs\validation\latest\cad_samples"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    PART_PATH = os.path.join(OUTPUT_DIR, "mounting_plate.SLDPRT")
    STEP_PATH = os.path.join(OUTPUT_DIR, "mounting_plate.step")

    # 连接SolidWorks
    print("连接SolidWorks实例...")
    sw_app = connect_solidworks()

    # 新建零件文档
    print("新建零件文档...")
    part_doc = new_document(sw_app, "part")

    # 绘制基体草图并拉伸
    print("创建基体特征...")
    start_sketch(part_doc, "Front Plane")
    # 绘制120x80mm矩形，原点在左下角
    sketch_rectangle(part_doc, mm(0), mm(0), mm(120), mm(80))
    end_sketch(part_doc)
    # 拉伸10mm形成基体
    extrude_boss(part_doc, mm(10))

    # 绘制通孔草图并拉伸切除
    print("创建安装通孔...")
    start_sketch(part_doc, "Front Plane")
    # M6通孔直径6.5mm，孔中心距边缘10mm
    hole_radius = mm(6.5) / 2
    hole_positions = [
        (mm(10), mm(10)),
        (mm(110), mm(10)),
        (mm(110), mm(70)),
        (mm(10), mm(70))
    ]
    for x, y in hole_positions:
        sketch_circle(part_doc, x, y, hole_radius)
    end_sketch(part_doc)
    # 完全贯穿拉伸切除
    extrude_cut(part_doc, through_all=True)

    # 添加外边缘倒角
    print("添加倒角特征...")
    chamfer(part_doc, mm(1), 45)

    # 保存零件
    print(f"保存零件到: {PART_PATH}")
    save_document(part_doc, PART_PATH)

    # 导出STEP
    print(f"导出STEP到: {STEP_PATH}")
    export_to_step(part_doc, STEP_PATH)

    # 验证文件
    if os.path.exists(PART_PATH) and os.path.exists(STEP_PATH):
        print("任务完成：文件已成功生成")
    else:
        print("警告：部分输出文件未找到")

if __name__ == "__main__":
    main()
