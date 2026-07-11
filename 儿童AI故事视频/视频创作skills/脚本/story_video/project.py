from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .common import ensure_project_dirs, load_json, save_json, update_manifest, validate_story


def initialize_project(
    project: Path,
    *,
    drawing: Path,
    story_path: Path,
    voice: Path | None,
    config: dict[str, Any],
) -> dict[str, Path]:
    if not drawing.exists():
        raise RuntimeError(f"找不到原画：{drawing}")
    if not story_path.exists():
        raise RuntimeError(f"找不到故事文件：{story_path}")
    if voice is not None and not voice.exists():
        raise RuntimeError(f"找不到声音文件：{voice}")

    story = load_json(story_path)
    validate_story(story)
    paths = ensure_project_dirs(project)

    drawing_target = paths["input"] / f"original_drawing{drawing.suffix.lower()}"
    if drawing.resolve() != drawing_target.resolve():
        shutil.copy2(drawing, drawing_target)

    copied_files = [drawing_target]
    if voice is not None:
        voice_target = paths["input"] / f"voice_reference{voice.suffix.lower()}"
        if voice.resolve() != voice_target.resolve():
            shutil.copy2(voice, voice_target)
        copied_files.append(voice_target)

    story_target = paths["text"] / "story.json"
    save_json(story_target, story)
    save_json(project / "project.json", {"config": config, "story_file": "text/story.json"})
    update_manifest(project, "init", copied_files + [story_target, project / "project.json"])
    return paths


def find_single_input(folder: Path, stem: str) -> Path:
    candidates = sorted(path for path in folder.glob(f"{stem}.*") if path.is_file())
    if not candidates:
        raise RuntimeError(f"项目中缺少 {stem} 文件。")
    return candidates[0]

