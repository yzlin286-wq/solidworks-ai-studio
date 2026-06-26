from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd()
VENDORED_SW_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
if VENDORED_SW_SCRIPTS.exists() and str(VENDORED_SW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SW_SCRIPTS))

import os
import sys

# 添加vendored脚本路径
sys.path.append(r'C:\Users\Vision\Documents\sw skill 应用化\vendor\skills\solidworks-automation\scripts')

from sw_session import session
from sw_part import (
    start_sketch, end_sketch, sketch_rectangle, sketch_circle,
    add_dimension, extrude_boss, extrude_cut, chamfer
)
from sw_connect import new_document, save_document, mm
from sw_export import export_to_step
from sw_review import run_review

# 配置参数
OUTPUT_DIR = r'C:\Users\Vision\Documents\sw skill 应用化\outputs\validation\latest\cad_samples'
PART_NAME = 'mounting_plate_120x80x10_M6'
PLATE_WIDTH = 120 * mm
PLATE_DEPTH = 80 * mm
PLATE_THICKNESS = 10 * mm
HOLE_DIAMETER = 6.6 * mm  # M6标准通孔
HOLE_EDGE_DISTANCE = 15 * mm  # 孔中心到边缘距离
CHAMFER_SIZE = 1 * mm

def main():
    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. 连接SolidWorks并创建新零件
    print("连接SolidWorks...")
    sw_app, model = session()
    
    print("创建新零件文档...")
    model = new_document(sw_app, 'part')
    
    # 2. 创建基体拉伸
    print("创建基体草图...")
    start_sketch(model, 'Front Plane')
    sketch_rectangle(model, 0, 0, PLATE_WIDTH, PLATE_DEPTH)
    # 添加尺寸约束
    add_dimension(model, 'Rectangle1', PLATE_WIDTH, 'D1@Sketch1')
    add_dimension(model, 'Rectangle1', PLATE_DEPTH, 'D2@Sketch1')
    end_sketch(model)
    
    print("拉伸基体...")
    extrude_boss(model, 'Sketch1', PLATE_THICKNESS)
    
    # 3. 创建四个通孔
    print("创建孔草图...")
    start_sketch(model, 'Boss-Extrude1', face_index=0)
    # 四个角的孔位置
    hole_positions = [
        (HOLE_EDGE_DISTANCE, HOLE_EDGE_DISTANCE),
        (PLATE_WIDTH - HOLE_EDGE_DISTANCE, HOLE_EDGE_DISTANCE),
        (HOLE_EDGE_DISTANCE, PLATE_DEPTH - HOLE_EDGE_DISTANCE),
        (PLATE_WIDTH - HOLE_EDGE_DISTANCE, PLATE_DEPTH - HOLE_EDGE_DISTANCE)
    ]
    for i, (x, y) in enumerate(hole_positions):
        sketch_circle(model, x, y, HOLE_DIAMETER / 2)
    end_sketch(model)
    
    print("拉伸切除通孔...")
    extrude_cut(model, 'Sketch2', PLATE_THICKNESS, through_all=True)
    
    # 4. 添加倒角
    print("添加外边缘倒角...")
    chamfer(model, 'Boss-Extrude1', CHAMFER_SIZE, edge_type='outer_edges')
    
    # 5. 保存零件
    sldprt_path = os.path.join(OUTPUT_DIR, f'{PART_NAME}.SLDPRT')
    print(f"保存零件到: {sldprt_path}")
    save_document(model, sldprt_path, save_as=True)
    
    # 6. 导出STEP
    step_path = os.path.join(OUTPUT_DIR, f'{PART_NAME}.step')
    print(f"导出STEP到: {step_path}")
    export_to_step(model, step_path)
    
    # 7. 运行审查
    print("生成模型审查报告...")
    run_review(model, OUTPUT_DIR, PART_NAME)
    
    print("任务完成!")
    print(f"创建的文件:")
    print(f"  - {sldprt_path}")
    print(f"  - {step_path}")
    print(f"  - 审查报告和预览图在 {OUTPUT_DIR}")

if __name__ == '__main__':
    main()
