from __future__ import annotations

import asyncio
import base64
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from PIL import Image, ImageFilter, ImageStat

from sw_ai_backend.core.config import ConfigStore
from sw_ai_backend.core.paths import project_root


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp"}


def visual_root() -> Path:
    root = project_root() / "outputs" / "visual_validation" / "latest"
    for child in [
        root / "screenshots" / "app",
        root / "screenshots" / "solidworks",
        root / "previews",
        root / "vision_prompts",
        root / "vision_results",
    ]:
        child.mkdir(parents=True, exist_ok=True)
    return root


def _copy_cad_previews(root: Path) -> list[Path]:
    copied: list[Path] = []
    cad_target = root / "screenshots" / "solidworks"
    for old in cad_target.glob("*"):
        if old.is_file():
            old.unlink()
    samples_root = project_root() / "outputs" / "validation" / "latest" / "cad_samples"
    sample_dirs = [path for path in samples_root.iterdir() if path.is_dir()] if samples_root.exists() else []
    timestamp_dirs = [path for path in sample_dirs if path.name[:8].isdigit()]
    roots = []
    if timestamp_dirs:
        roots.append(max(timestamp_dirs, key=lambda item: item.stat().st_mtime))
    nl_review = samples_root / "nl_review"
    if nl_review.exists():
        roots.append(nl_review)
    tasks_root = project_root() / "outputs" / "tasks"
    task_review_dirs = [path for path in tasks_root.glob("*/review") if path.is_dir()] if tasks_root.exists() else []
    if task_review_dirs:
        roots.append(max(task_review_dirs, key=lambda item: item.stat().st_mtime))
    for source in sorted({bmp for candidate in roots for bmp in candidate.rglob("*.bmp")}):
        target = cad_target / source.name
        if target.exists():
            stem = source.stem
            index = 2
            while target.exists():
                target = cad_target / f"{stem}_{index}{source.suffix}"
                index += 1
        shutil.copy2(source, target)
        copied.append(target)
    return copied


def _image_metrics(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        image = image.convert("RGB")
        stat = ImageStat.Stat(image)
        gray = image.convert("L")
        gray_stat = ImageStat.Stat(gray)
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_stat = ImageStat.Stat(edges)
        width, height = image.size
        variance = float(sum(gray_stat.var) / len(gray_stat.var))
        edge_mean = float(sum(edge_stat.mean) / len(edge_stat.mean))
        return {
            "file_path": str(path),
            "created_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            "screenshot_size": {"width": width, "height": height},
            "file_size": path.stat().st_size,
            "pixel_variance": variance,
            "edge_mean": edge_mean,
            "non_blank": path.stat().st_size > 10_000 and width >= 400 and height >= 300 and variance > 5.0,
            "local_cv_pass": path.stat().st_size > 10_000 and width >= 400 and height >= 300 and variance > 5.0 and edge_mean > 0.5,
        }


async def _vision_analyze_one(path: Path, expected: str) -> dict[str, Any]:
    config = ConfigStore().load()
    profile = next((p for p in config.profiles if p.id == config.active_profile_id), config.profiles[0])
    if not profile.api_key:
        raise RuntimeError("No API key is configured for the active LLM profile.")
    vision_model = profile.vision_model or profile.model
    image_bytes = path.read_bytes()
    mime = "image/png" if path.suffix.lower() == ".png" else "image/bmp" if path.suffix.lower() == ".bmp" else "image/jpeg"
    prompt = {
        "image_path": str(path),
        "expected": expected,
        "instructions": "Return strict JSON with image_path, expected, observed, pass, confidence, issues, evidence. Do not include secrets.",
    }
    payload = {
        "model": vision_model,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": json.dumps(prompt, ensure_ascii=False)},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{base64.b64encode(image_bytes).decode('ascii')}"
                        },
                    },
                ],
            }
        ],
        "response_format": {"type": "json_object"},
    }
    async with httpx.AsyncClient(timeout=profile.timeout_seconds) as client:
        response = await client.post(
            f"{profile.api_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {profile.api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
    content = data["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    parsed.setdefault("image_path", str(path))
    parsed.setdefault("expected", expected)
    parsed.setdefault("vision_model", vision_model)
    return parsed


def _expected_for(path: Path) -> str:
    lower = path.name.lower()
    if "mounting" in lower or "plate" in lower:
        if "front" in lower or "isometric" in lower:
            return "A SolidWorks mounting plate preview with rectangular body and four visible holes."
        if "top" in lower or "right" in lower:
            return "A SolidWorks side or edge projection of the mounting plate; holes may be hidden by the viewing direction, but the plate body must be visible."
        return "A SolidWorks mounting plate preview with rectangular body and holes."
    if "cylinder" in lower or "shaft" in lower:
        return "A long cylindrical shaft preview."
    if "assembly" in lower:
        return "A SolidWorks assembly preview with at least two components."
    if path.suffix.lower() == ".png":
        return "A non-empty SolidWorks AI Studio packaged desktop UI screenshot with real status text."
    return "A non-empty SolidWorks/CAD preview image."


def _is_app_image(path: Path) -> bool:
    normalized = str(path).lower()
    return "\\app\\" in normalized or "/app/" in normalized


def _select_vision_paths(image_paths: list[Path], max_images: int) -> list[Path]:
    if max_images <= 0:
        return []
    if len(image_paths) <= max_images:
        return image_paths
    app_images = [path for path in image_paths if _is_app_image(path)]
    cad_images = [path for path in image_paths if not _is_app_image(path)]
    if not app_images or not cad_images:
        return image_paths[:max_images]
    app_quota = max(1, max_images // 2)
    cad_quota = max_images - app_quota
    selected = app_images[:app_quota] + cad_images[:cad_quota]
    if len(selected) < max_images:
        selected.extend(path for path in image_paths if path not in selected)
    return selected[:max_images]


async def run_visual_validation_async() -> dict[str, Any]:
    root = visual_root()
    _copy_cad_previews(root)
    for old in (root / "vision_results").glob("*.json"):
        old.unlink()
    image_paths = sorted(path for path in (root / "screenshots").rglob("*") if path.suffix.lower() in IMAGE_SUFFIXES)
    local_results = []
    for path in image_paths:
        try:
            local_results.append(_image_metrics(path))
        except Exception as exc:
            local_results.append({"file_path": str(path), "local_cv_pass": False, "error": str(exc)})

    local_ok = bool(local_results) and all(item.get("local_cv_pass") for item in local_results)
    local_payload = {
        "local_cv_ok": local_ok,
        "generated_at": datetime.now().isoformat(),
        "image_count": len(local_results),
        "results": local_results,
    }
    (root / "local_cv_report.json").write_text(json.dumps(local_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_local_md(local_payload, root / "local_cv_report.md")

    vision_results: list[dict[str, Any]] = []
    vision_errors: list[dict[str, str]] = []
    max_vision_images = max(0, int(os.environ.get("SWAI_VISUAL_MAX_VISION_IMAGES", "24")))
    if os.environ.get("SWAI_VISUAL_SKIP_VISION") == "1":
        max_vision_images = 0
    for path in _select_vision_paths(image_paths, max_vision_images):
        try:
            result = await _vision_analyze_one(path, _expected_for(path))
            vision_results.append(result)
            (root / "vision_results" / f"{path.stem}.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            vision_errors.append({"image_path": str(path), "error": str(exc)[:500]})

    vision_ok = bool(vision_results) and not vision_errors and all(bool(item.get("pass")) for item in vision_results)
    degraded = bool(vision_errors)
    app_screenshots = [item for item in local_results if "\\app\\" in item.get("file_path", "").lower() or "/app/" in item.get("file_path", "").lower()]
    cad_screenshots = [item for item in local_results if "\\solidworks\\" in item.get("file_path", "").lower() or "/solidworks/" in item.get("file_path", "").lower()]
    config = ConfigStore().load()
    active_profile = next((p for p in config.profiles if p.id == config.active_profile_id), config.profiles[0])
    payload = {
        "visual_ok": local_ok and vision_ok,
        "degraded": degraded,
        "generated_at": datetime.now().isoformat(),
        "app_screenshot_count": len(app_screenshots),
        "cad_screenshot_count": len(cad_screenshots),
        "local_cv_check_count": len(local_results),
        "vision_analysis_count": len(vision_results),
        "vision_error_count": len(vision_errors),
        "vision_model": active_profile.vision_model or active_profile.model,
        "local_cv_report": str(root / "local_cv_report.json"),
        "vision_results": vision_results,
        "vision_errors": vision_errors,
        "images": local_results,
        "conclusion": (
            "视觉验证通过。"
            if local_ok and vision_ok
            else "视觉验证降级或失败；不能声称视觉分析已完成。"
        ),
    }
    (root / "VISUAL_VALIDATION_REPORT.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_visual_md(payload, root / "VISUAL_VALIDATION_REPORT.md")
    return payload


def _write_local_md(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# 本地 CV 报告",
        "",
        f"生成时间：{payload['generated_at']}",
        f"本地 CV 通过：{payload['local_cv_ok']}",
        f"检查图片数：{payload['image_count']}",
        "",
        "| 图片 | 通过 | 尺寸 | 像素方差 | 边缘均值 |",
        "|---|---:|---|---:|---:|",
    ]
    for item in payload["results"]:
        size = item.get("screenshot_size", {})
        lines.append(
            f"| `{item.get('file_path')}` | {item.get('local_cv_pass')} | {size.get('width')}x{size.get('height')} | "
            f"{item.get('pixel_variance', 0):.2f} | {item.get('edge_mean', 0):.2f} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_visual_md(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# 视觉验证报告",
        "",
        f"生成时间：{payload['generated_at']}",
        f"视觉验证通过：{payload['visual_ok']}",
        f"是否降级：{payload['degraded']}",
        f"结论：{payload['conclusion']}",
        "",
        f"- App 截图：{payload['app_screenshot_count']}",
        f"- CAD 截图：{payload['cad_screenshot_count']}",
        f"- 本地 CV 检查：{payload['local_cv_check_count']}",
        f"- Vision 分析：{payload['vision_analysis_count']}",
        f"- Vision 错误：{payload['vision_error_count']}",
        f"- Vision 模型：{payload.get('vision_model', '')}",
        "",
        "## Vision 错误",
    ]
    if payload["vision_errors"]:
        for item in payload["vision_errors"]:
            lines.append(f"- `{item['image_path']}`: {item['error']}")
    else:
        lines.append("- 无")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    payload = asyncio.run(run_visual_validation_async())
    print(json.dumps({"visual_ok": payload["visual_ok"], "degraded": payload["degraded"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
