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
        import http.client
        import urllib.error
        import time
        
        image_bytes = None
        max_download_retries = 10
        for attempt in range(max_download_retries):
            try:
                req = urllib.request.Request(
                    item["url"],
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
                )
                with urllib.request.urlopen(req, timeout=120) as response:
                    image_bytes = response.read()
                break
            except Exception as err:
                if attempt == max_download_retries - 1:
                    raise
                print(f"下载图片失败，正在重试 ({attempt + 1}/{max_download_retries})：{err}", flush=True)
                time.sleep(5)
        if not image_bytes:
            raise RuntimeError("下载图片失败，未获取到数据。")
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


def _get_font(font_size: int) -> Any:
    from PIL import ImageFont
    import os
    import sys
    
    if sys.platform.startswith("win"):
        windir = os.environ.get("windir", "C:\\Windows")
        candidates = [
            os.path.join(windir, "Fonts", "msyh.ttc"),      # 微软雅黑
            os.path.join(windir, "Fonts", "msyhbd.ttc"),    # 微软雅黑粗体
            os.path.join(windir, "Fonts", "simsun.ttc"),    # 宋体
            os.path.join(windir, "Fonts", "simhei.ttf"),    # 黑体
        ]
    else:
        candidates = [
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/Supplemental/Songti.ttc",
        ]
        
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, font_size)
            except Exception:
                pass
                
    # 尝试按名称直接加载系统安装过的字体
    for name in ["msyh", "Microsoft YaHei", "Arial Unicode MS", "PingFang SC", "SimHei"]:
        try:
            return ImageFont.truetype(name, font_size)
        except Exception:
            pass
            
    return ImageFont.load_default()


def _add_name_to_image(image_path: Path, name: str) -> None:
    from PIL import Image, ImageDraw, ImageFont
    import re
    
    img = Image.open(image_path)
    width, height = img.size
    
    font_size = max(24, int(width * 0.045))
    font = _get_font(font_size)
        
    draw = ImageDraw.Draw(img)
    try:
        bbox = draw.textbbox((0, 0), name, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    except AttributeError:
        text_w, text_h = draw.textsize(name, font=font)
        
    padding_x = int(font_size * 0.6)
    padding_y = int(font_size * 0.3)
    
    box_w = text_w + 2 * padding_x
    box_h = text_h + 2 * padding_y
    
    box_x1 = (width - box_w) // 2
    box_y1 = height - int(height * 0.08) - box_h
    box_x2 = box_x1 + box_w
    box_y2 = box_y1 + box_h
    
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    radius = int(box_h * 0.25)
    overlay_draw.rounded_rectangle(
        [box_x1, box_y1, box_x2, box_y2],
        radius=radius,
        fill=(0, 0, 0, 160)
    )
    
    img_rgba = Image.alpha_composite(img.convert("RGBA"), overlay)
    
    draw_final = ImageDraw.Draw(img_rgba)
    text_x = box_x1 + padding_x
    text_y = box_y1 + padding_y - int(font_size * 0.05)
    draw_final.text((text_x, text_y), name, fill=(255, 255, 255, 255), font=font)
    
    img_rgba.convert("RGB").save(image_path, "JPEG")


def _generate_ending_slide(title: str, creator: str, output_path: Path, config: dict[str, Any]) -> None:
    """生成留白充足、以标题和创作者署名为主的结尾作品页。"""
    from PIL import Image, ImageDraw

    image_config = config["image"]
    width = int(image_config["width"])
    height = int(image_config["height"])
    img = Image.new("RGB", (width, height), color=(16, 29, 60))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        ratio = y / height
        draw.line([(0, y), (width, y)], fill=(int(16 + 30 * ratio), int(29 + 9 * ratio), int(60 + 38 * ratio)))

    # 只在边缘布置少量星光，中央留白交给标题和署名。
    sparkles = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sparkle_draw = ImageDraw.Draw(sparkles)
    for index in range(20):
        x = (index * 437 + 113) % width
        y = ((index * 251 + 73) % int(height * 0.30)) if index < 10 else int(height * 0.76) + ((index * 137) % int(height * 0.17))
        radius = 2 + (index % 3) * 2
        color = (255, 230, 163, 90 + (index % 3) * 40)
        sparkle_draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=color)
        if index % 6 == 0:
            sparkle_draw.line([x - radius * 3, y, x + radius * 3, y], fill=color, width=1)
            sparkle_draw.line([x, y - radius * 3, x, y + radius * 3], fill=color, width=1)
    img = Image.alpha_composite(img.convert("RGBA"), sparkles).convert("RGB")
    draw = ImageDraw.Draw(img)

    gold = (244, 207, 128)
    cream = (255, 247, 224)
    # 成片主要在手机竖屏直接观看；创作者名是最大视觉信息，不能依赖用户放大阅读。
    font_kicker = _get_font(max(34, int(width * 0.036)))
    font_title = _get_font(max(74, int(width * 0.084)))
    creator_font_size = max(88, int(width * 0.102))
    font_creator = _get_font(creator_font_size)
    font_caption = _get_font(max(34, int(width * 0.036)))
    title_text = f"《{title}》"
    creator_text = creator or "无名创作者"

    # 顶部的小标识建立仪式感，细线与标题形成清楚的阅读起点。
    kicker = "STORY COMPLETE"
    kicker_box = draw.textbbox((0, 0), kicker, font=font_kicker)
    kicker_w = kicker_box[2] - kicker_box[0]
    kicker_y = int(height * 0.22)
    draw.text(((width - kicker_w) // 2, kicker_y), kicker, fill=gold, font=font_kicker)
    line_y = kicker_y + int(height * 0.045)
    line_w = int(width * 0.12)
    draw.line([(width // 2 - line_w, line_y), (width // 2 + line_w, line_y)], fill=gold, width=max(2, int(width * 0.002)))

    # 长标题最多折为两行，始终保留舒适的左右边距。
    max_title_width = int(width * 0.86)
    title_lines = [title_text]
    title_box = draw.textbbox((0, 0), title_text, font=font_title)
    if title_box[2] - title_box[0] > max_title_width and len(title_text) > 4:
        midpoint = len(title_text) // 2
        title_lines = [title_text[:midpoint], title_text[midpoint:]]
    title_y = int(height * 0.36)
    line_gap = int(height * 0.018)
    for line in title_lines:
        box = draw.textbbox((0, 0), line, font=font_title)
        text_w, text_h = box[2] - box[0], box[3] - box[1]
        draw.text(((width - text_w) // 2 + 2, title_y + 3), line, fill=(8, 14, 34), font=font_title)
        draw.text(((width - text_w) // 2, title_y), line, fill=cream, font=font_title)
        title_y += text_h + line_gap

    # 署名独占一行，以大字号成为结尾页最醒目的信息。
    author_label = "创作者"
    label_box = draw.textbbox((0, 0), author_label, font=font_caption)
    creator_box = draw.textbbox((0, 0), creator_text, font=font_creator)
    while creator_box[2] - creator_box[0] > int(width * 0.82) and creator_font_size > 60:
        creator_font_size -= 4
        font_creator = _get_font(creator_font_size)
        creator_box = draw.textbbox((0, 0), creator_text, font=font_creator)
    author_y = max(int(height * 0.63), title_y + int(height * 0.08))
    label_w = label_box[2] - label_box[0]
    creator_w = creator_box[2] - creator_box[0]
    draw.text(((width - label_w) // 2, author_y), author_label, fill=(218, 190, 123), font=font_caption)
    creator_y = author_y + (label_box[3] - label_box[1]) + int(height * 0.028)
    draw.text(((width - creator_w) // 2 + 3, creator_y + 4), creator_text, fill=(7, 13, 30), font=font_creator)
    draw.text(((width - creator_w) // 2, creator_y), creator_text, fill=cream, font=font_creator)
    rule_y = creator_y + (creator_box[3] - creator_box[1]) + int(height * 0.030)
    draw.line([(int(width * 0.22), rule_y), (int(width * 0.78), rule_y)], fill=(203, 168, 94), width=max(3, int(width * 0.0025)))

    closing = "感谢观看"
    closing_box = draw.textbbox((0, 0), closing, font=font_caption)
    draw.text(((width - (closing_box[2] - closing_box[0])) // 2, int(height * 0.86)), closing, fill=(225, 229, 239), font=font_caption)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=95)


def _character_reference_paths(paths: dict[str, Path], characters: list[dict[str, Any]]) -> list[Path]:
    return [paths["images"] / f"角色参考_{index}.jpg" for index, _ in enumerate(characters, 1)]


def _generate_character_references(
    *,
    paths: dict[str, Path],
    characters: list[dict[str, Any]],
    style: str,
    normalized: Path,
    config: dict[str, Any],
    force: bool,
) -> list[Path]:
    """生成可单独审核的角色原型；场景生成阶段只复用这些已确认的文件。"""
    character_paths: list[Path] = []
    for idx, char in enumerate(characters, 1):
        name = char.get("name", f"角色_{idx}")
        subject_type = str(char.get("subject_type", "object")).strip().lower()
        non_human_guard = ""
        if subject_type != "person":
            non_human_guard = (
                f"主角类型是 {subject_type}，主角就是这个主体本身。"
                "不要添加人类头部、身体或操作者，不要把它改造成穿着该物体的人，也不要新增人类主角。"
                "画面中不得出现任何人类、人形角色、人脸或人手。"
            )

        char_img_path = paths["images"] / f"角色参考_{idx}.jpg"
        if force and char_img_path.exists():
            char_img_path.unlink()
        if not char_img_path.exists():
            prompt = (
                "根据输入的原画制作一张角色原型图，供创作者先确认角色是否正确。"
                f"角色名：{name}。"
                f"外形：{char.get('appearance', '')}。"
                f"特别之处：{char.get('special_ability', '')}。"
                f"画面风格：{style}。"
                f"{non_human_guard}"
                "保留原画最有辨识度的轮廓、颜色、结构和朴拙手绘气质；单一角色完整入镜，"
                "简单浅色背景，竖版3:4，无文字、无字幕、无水印。"
            )
            print(f"正在生成角色【{name}】的原型图……")
            _generate_image(prompt=prompt, references=[normalized], output=char_img_path, config=config)
            try:
                _add_name_to_image(char_img_path, name)
                print(f"已在角色【{name}】原型图上印写名字")
            except Exception as err:
                print(f"在图片上印写角色【{name}】的名字失败：{err}")
        character_paths.append(char_img_path)
    return character_paths


def generate_prototypes(
    project: Path,
    *,
    config: dict[str, Any],
    force: bool = False,
) -> list[Path]:
    """第二阶段：只生成角色原型，让创作者确认后再生成四幕场景。"""
    from .docx_helper import sync_docx_to_json
    sync_docx_to_json(project)
    paths = ensure_project_dirs(project)
    story = load_json(paths["text"] / "故事.json")
    original = find_single_input(paths["input"], "原始手绘")
    normalized = _normalize_drawing(original, paths["work"] / "手绘参考.jpg")
    characters = story.get("characters", []) or ([story["character"]] if story.get("character") else [])
    if not characters:
        raise RuntimeError("故事缺少角色设定，无法生成角色原型。")
    outputs = _generate_character_references(
        paths=paths,
        characters=characters,
        style=story.get("style", "温暖手绘绘本"),
        normalized=normalized,
        config=config,
        force=force,
    )
    update_manifest(project, "prototype", outputs)
    return outputs


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

    characters = story.get("characters", [])
    if not characters and "character" in story:
        characters = [story["character"]]

    style = story.get("style", "温暖手绘绘本")
    character_paths = _character_reference_paths(paths, characters)
    missing_prototypes = [path.name for path in character_paths if not path.exists()]
    if missing_prototypes:
        raise RuntimeError(
            "缺少已确认的角色原型：" + "、".join(missing_prototypes)
            + "。请先运行 prototype 生成并由创作者确认角色原型。"
        )

    # 2. 场景图片生成
    selected = {scene} if scene else set(range(1, len(story["scenes"]) + 1))
    outputs: list[Path] = []
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
            
        ref_descr = ""
        for i, char in enumerate(characters, 1):
            ref_descr += f"图{i+1}是角色【{char.get('name')}】的标准参考图。 "
            
        subject_type = str(characters[0].get("subject_type", "object")).strip().lower() if characters else "object"
        non_human_guard = ""
        if subject_type != "person":
            non_human_guard = (
                f"主角类型是 {subject_type}，主角就是这个主体本身。"
                "不要添加人类头部、身体或操作者，不要把它改造成穿着该物体的人，也不要新增人类主角。"
                "画面中不得出现任何人类、人形角色、人脸或人手。"
            )
            
        prompt = (
            f"图1是创作者提供的原画。{ref_descr}请生成包含上述角色的故事场景，"
            "严格保留各个角色的辨识度、主要颜色、结构 and 手绘气质，不要重新设计角色。"
            f"{non_human_guard}"
            f"故事场景：{scene_data['visual_prompt']}。"
            f"统一风格：{style}。"
            "主体清楚，适合日常竖版故事分享，竖版3:4构图。所有动作只用画面表现，"
            "不要把提示词、动作、声音或故事内容写在图片里；无文字、无字母、无数字、无字幕、无水印。"
            f"最终硬性检查：{non_human_guard}"
        )
        print(f"正在生成第 {index} 幕图片……")
        _generate_image(
            prompt=prompt,
            references=[normalized] + character_paths,
            output=output,
            config=config,
        )
        outputs.append(output)

    # 3. 动态生成结尾作品页图片
    ending_path = paths["images"] / "结尾页.jpg"
    title = story.get("title", "未命名故事")
    creator = story.get("creator_display", "无名创作者")
    print(f"正在生成故事【{title}】结尾页（创作者：{creator}）……")
    try:
        _generate_ending_slide(title, creator, ending_path, config)
        outputs.append(ending_path)
        print(f"结尾页生成完毕，已保存至: {ending_path}")
    except Exception as err:
        print(f"生成结尾页失败：{err}")

    update_manifest(project, "images", outputs)
    return outputs
