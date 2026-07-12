from __future__ import annotations

import base64
import urllib.request
from pathlib import Path
from typing import Any

from .common import (
    ensure_project_dirs,
    http_json,
    image_data_uri,
    load_json,
    require_command,
    require_env,
    run_command,
    update_manifest,
)
from .project import find_single_input


ARK_IMAGE_URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"


def _normalize_drawing(source: Path, target: Path) -> Path:
    if target.exists():
        return target
    require_command("ffmpeg")
    run_command(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(source),
            "-vf", "scale=1600:1600:force_original_aspect_ratio=decrease",
            "-frames:v", "1", "-q:v", "2", str(target),
        ]
    )
    return target


def _generate_image(
    *,
    prompt: str,
    references: list[Path],
    output: Path,
    config: dict[str, Any],
) -> Path:
    image_config = config["image"]
    width = int(image_config["width"])
    height = int(image_config["height"])
    if width * height < 3_686_400:
        raise RuntimeError("豆包当前要求图片至少 3686400 像素，请提高 config.json 中的尺寸。")

    payload = {
        "model": image_config["model"],
        "prompt": prompt,
        "image": [image_data_uri(path) for path in references],
        "size": f"{width}x{height}",
        "sequential_image_generation": "disabled",
        "response_format": "b64_json",
        "watermark": bool(image_config.get("watermark", False)),
    }
    data = http_json(
        ARK_IMAGE_URL,
        payload=payload,
        headers={
            "Authorization": f"Bearer {require_env('VOLCENGINE_API_KEY')}",
            "Content-Type": "application/json",
        },
        timeout=int(image_config.get("timeout_seconds", 300)),
        retries=int(image_config.get("max_retries", 2)),
    )
    item = (data.get("data") or [{}])[0]
    raw = item.get("b64_json")
    if raw:
        image_bytes = base64.b64decode(raw)
    elif item.get("url"):
        with urllib.request.urlopen(item["url"], timeout=120) as response:
            image_bytes = response.read()
    else:
        raise RuntimeError("豆包接口没有返回图片。")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(image_bytes)
    return output


def _build_contact_sheet(scene_paths: list[Path], output: Path) -> Path:
    require_command("ffmpeg")
    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for path in scene_paths:
        command.extend(["-i", str(path)])
    filters = []
    for index in range(4):
        filters.append(
            f"[{index}:v]scale=540:720:force_original_aspect_ratio=increase,"
            f"crop=540:720[s{index}]"
        )
    filters.append(
        "[s0][s1][s2][s3]xstack=inputs=4:layout=0_0|540_0|0_720|540_720[v]"
    )
    command.extend([
        "-filter_complex", ";".join(filters),
        "-map", "[v]", "-frames:v", "1", "-q:v", "2", str(output),
    ])
    run_command(command)
    return output


def generate_images(
    project: Path,
    *,
    config: dict[str, Any],
    scene: int | None = None,
    force: bool = False,
) -> list[Path]:
    from .docx_helper import sync_docx_to_json
    sync_docx_to_json(project)
    paths = ensure_project_dirs(project)
    story = load_json(paths["text"] / "故事.json")
    original = find_single_input(paths["input"], "原始手绘")
    normalized = _normalize_drawing(original, paths["work"] / "手绘参考.jpg")

    character = story["character"]
    subject_type = str(character.get("subject_type", "object")).strip().lower()
    style = story.get("style", "温暖童趣的手绘绘本")
    non_human_guard = ""
    if subject_type != "person":
        non_human_guard = (
            f"主角类型是 {subject_type}，主角就是这个主体本身。"
            "不要添加人类头部、身体或操作者，不要把它改造成穿着该物体的人，也不要新增人类主角。"
            "画面中不得出现任何人类、儿童、人形角色、人脸或人手。"
        )
    character_path = paths["images"] / "角色参考.jpg"
    if force and scene is None and character_path.exists():
        character_path.unlink()
    if not character_path.exists():
        prompt = (
            "根据输入的孩子原画制作一张角色标准参考图。"
            f"角色名：{character['name']}。"
            f"外形：{character.get('appearance', '')}。"
            f"特别之处：{character.get('special_ability', '')}。"
            f"画面风格：{style}。"
            f"{non_human_guard}"
            "保留原画最有辨识度的轮廓、颜色、结构和朴拙手绘气质；单一角色完整入镜，"
            "简单浅色背景，竖版3:4，无文字、无字幕、无水印。"
        )
        print("正在生成角色标准图……")
        _generate_image(prompt=prompt, references=[normalized], output=character_path, config=config)

    selected = {scene} if scene else {1, 2, 3, 4}
    outputs: list[Path] = [character_path]
    for scene_data in story["scenes"]:
        index = int(scene_data["index"])
        output = paths["images"] / f"场景_{index:02d}.jpg"
        if index not in selected:
            if output.exists():
                outputs.append(output)
            continue
        if output.exists() and not force:
            print(f"第 {index} 幕图片已存在，跳过。")
            outputs.append(output)
            continue
        prompt = (
            "图1是孩子原画，图2是同一角色的标准参考图。请生成同一角色的故事场景，"
            "严格保留角色的辨识度、主要颜色、结构 and 手绘气质，不要重新设计角色。"
            f"{non_human_guard}"
            f"故事场景：{scene_data['visual_prompt']}。"
            f"统一风格：{style}。"
            "主体清楚，适合小学阶段儿童，竖版3:4构图。所有动作只用画面表现，"
            "不要把提示词、动作、声音或故事内容写在图片里；无文字、无字母、无数字、无字幕、无水印。"
            f"最终硬性检查：{non_human_guard}"
        )
        print(f"正在生成第 {index} 幕图片……")
        _generate_image(
            prompt=prompt,
            references=[normalized, character_path],
            output=output,
            config=config,
        )
        outputs.append(output)

    update_manifest(project, "images", outputs)
    return outputs
