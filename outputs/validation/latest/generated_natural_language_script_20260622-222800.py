from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd()
VENDORED_SW_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
if VENDORED_SW_SCRIPTS.exists() and str(VENDORED_SW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SW_SCRIPTS))

import os
from sw_connect import connect_solidworks, new_document, save_document, mm
from sw_part import start_sketch, end_sketch, sketch_corner_rectangle, extrude_boss, sketch_circle, extrude_cut, chamfer
from sw_export import export_to_step

# 配置输出路径
OUTPUT_DIR = r"C:\Users\Vision\Documents\sw skill 应用化\outputs\validation\latest\cad_samples"
PART_FILENAME = "安装板_120x80x10_M6通孔.SLDPRT"
STEP_FILENAME = "安装板_120x80x10_M6通孔.STEP"

# 创建输出目录（如不存在）
os.makedirs(OUTPUT_DIR, exist_ok=True)
part_save_path = os.path.join(OUTPUT_DIR, PART_FILENAME)
step_save_path = os.path.join(OUTPUT_DIR, STEP_FILENAME)

def main():
    # 连接SolidWorks实例
    sw_app = connect_solidworks()
    if not sw_app:
        raise RuntimeError("无法连接到SolidWorks，请确保SolidWorks正在运行")
    
    # 新建零件文档
    part_doc = new_document(sw_app, "part")
    if not part_doc:
        raise RuntimeError("无法创建新的零件文档")
    
    try:
        # 1. 创建安装板基体：120x80x10mm
        start_sketch(part_doc, "Front Plane")
        sketch_corner_rectangle(0, 0, 120 * mm, 80 * mm)
        end_sketch(part_doc)
        extrude_boss(part_doc, depth=10 * mm)
        
        # 2. 创建四角M6通孔（直径6mm，完全贯穿）
        start_sketch(part_doc, "Front Plane")
        hole_radius = 3 * mm  # M6通孔直径6mm，半径3mm
        # 孔中心距离板边缘10mm
        sketch_circle(10 * mm, 10 * mm, hole_radius)
        sketch_circle(110 * mm, 10 * mm, hole_radius)
        sketch_circle(10 * mm, 70 * mm, hole_radius)
        sketch_circle(110 * mm, 70 * mm, hole_radius)
        end_sketch(part_doc)
        extrude_cut(part_doc, through_all=True)
        
        # 3. 添加1mm×45°倒角
        chamfer(part_doc, distance=1 * mm, angle=45)
        
        # 4. 保存零件
        save_document(part_doc, part_save_path)
        print(f"零件已保存: {part_save_path}")
        
        # 5. 导出STEP文件
        export_to_step(part_doc, step_save_path)
        print(f"STEP已导出: {step_save_path}")
        
        print("安装板创建完成！")
        
    except Exception as e:
        raise RuntimeError(f"模型创建失败: {str(e)}") from e

if __name__ == "__main__":
    main()