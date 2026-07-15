from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .common import ensure_project_dirs, load_json, save_json, update_manifest, validate_story


def initialize_project(
    project: Path,
    *,
    drawing: Path | None,
    story_path: Path,
    voice: Path | None,
    config: dict[str, Any],
) -> dict[str, Path]:
    if drawing is not None and not drawing.exists():
        raise RuntimeError(f"找不到原画：{drawing}")
    if not story_path.exists():
        raise RuntimeError(f"找不到故事文件：{story_path}")
    if voice is not None and not voice.exists():
        raise RuntimeError(f"找不到声音文件：{voice}")

    story = load_json(story_path)
    validate_story(story)
    
    if "characters" not in story and "character" in story:
        story["characters"] = [story["character"]]
    elif "characters" in story and "character" not in story and story["characters"]:
        story["character"] = story["characters"][0]
        
    paths = ensure_project_dirs(project)

    copied_files: list[Path] = []
    if drawing is not None:
        drawing_target = paths["input"] / f"原始手绘{drawing.suffix.lower()}"
        if drawing.resolve() != drawing_target.resolve():
            shutil.copy2(drawing, drawing_target)
        copied_files.append(drawing_target)
    if voice is not None:
        voice_target = paths["input"] / f"声音参考{voice.suffix.lower()}"
        if voice.resolve() != voice_target.resolve():
            shutil.copy2(voice, voice_target)
        copied_files.append(voice_target)

    story_target = paths["text"] / "故事.json"
    save_json(story_target, story)
    save_json(project / ".工作" / "项目配置.json", {"config": config, "story_file": ".工作/故事.json"})
    update_manifest(project, "init", copied_files + [story_target, project / ".工作" / "项目配置.json"])
    return paths


def find_single_input(folder: Path, stem: str) -> Path:
    candidates = sorted(path for path in folder.glob(f"{stem}.*") if path.is_file())
    if not candidates:
        raise RuntimeError(f"项目中缺少 {stem} 文件。")
    return candidates[0]
