from __future__ import annotations

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("SWAI_PROJECT_ROOT") or getattr(sys, "_MEIPASS", "") or Path.cwd())
VENDORED_SW_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
if VENDORED_SW_SCRIPTS.exists() and str(VENDORED_SW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SW_SCRIPTS))

import os
# 导入vendored SolidWorks自动化模块
from sw_connect import connect_solidworks, new_document, save_document, mm
from sw_part import (
    start_sketch, end_sketch, sketch_corner_rectangle,
    extrude_boss, sketch_circle, extrude_cut, chamfer
)
from sw_export import export_to_step
from sw_review import run_review

# 配置输出路径
OUTPUT_DIR = r'C:\Users\Vision\Documents\sw skill 应用化\outputs\validation\latest\cad_samples'
PART_NAME = 'mounting_plate_120x80x10_M6'
SLDPRT_PATH = os.path.join(OUTPUT_DIR, f'{PART_NAME}.SLDPRT')
STEP_PATH = os.path.join(OUTPUT_DIR, f'{PART_NAME}.step')

def main():
    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 连接SolidWorks
    sw_app = connect_solidworks()
    if not sw_app:
        raise RuntimeError('无法连接到SolidWorks实例')
    
    try:
        # 新建零件文档
        part_doc = new_document(sw_app, 'part')
        if not part_doc:
            raise RuntimeError('无法创建新零件文档')
        
        # 1. 创建基础板：120x80x10mm
        start_sketch(part_doc, 'Front Plane')
        # 绘制左下角在原点的矩形
        sketch_corner_rectangle(part_doc, 0, 0, 120 * mm, 80 * mm)
        end_sketch(part_doc)
        extrude_boss(part_doc, depth=10 * mm)
        
        # 2. 创建四个M6通孔：中心距边缘10mm，孔径φ6.5mm
        start_sketch(part_doc, 'Top Plane')
        hole_centers = [
            (10 * mm, 10 * mm),
            (110 * mm, 10 * mm),
            (10 * mm, 70 * mm),
            (110 * mm, 70 * mm)
        ]
        for x, y in hole_centers:
            sketch_circle(part_doc, x, y, 3.25 * mm)  # M6通孔标准半径
        end_sketch(part_doc)
        # 贯穿切除整个板厚
        extrude_cut(part_doc, depth=10 * mm)
        
        # 3. 添加1mm外棱边倒角（45度）
        chamfer(part_doc, distance=1 * mm, angle=45.0, select_outer_edges=True)
        
        # 4. 保存SLDPRT
        save_document(part_doc, SLDPRT_PATH, save_as=True)
        
        # 5. 导出STEP
        export_to_step(part_doc, STEP_PATH)
        
        # 6. 运行模型审查
        run_review(part_doc, output_dir=OUTPUT_DIR)
        
        print(f'任务完成！生成文件：\n{SLDPRT_PATH}\n{STEP_PATH}')
        print('审查报告已生成到输出目录')
        
    finally:
        # 保持SolidWorks文档打开供用户验证
        pass

if __name__ == '__main__':
    main()