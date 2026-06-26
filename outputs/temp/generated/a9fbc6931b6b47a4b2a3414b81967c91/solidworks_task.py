from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SKILL_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))


def main() -> int:
    prompt = """新建一个 120 x 80 x 10 mm 安装板，四角各打 M6 通孔，倒角 1 mm，保存为 SLDPRT 并导出 STEP。"""
    output_dir = Path(r"C:\Users\Vision\Documents\sw skill 应用化\outputs\temp\generated\a9fbc6931b6b47a4b2a3414b81967c91\outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    plan_path = output_dir / "demo_solidworks_plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "mode": "mock",
                "prompt": prompt,
                "message": "SolidWorks 未连接。本次 dry run 用于验证队列、日志和输出处理。",
                "recommended_imports": ["sw_session.SolidWorksSession", "sw_part", "sw_export", "sw_review"],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"Demo 执行已写入 {plan_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
