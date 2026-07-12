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
    from PIL import Image, ImageDraw
    
    image_config = config["image"]
    width = int(image_config["width"])
    height = int(image_config["height"])
    
    img = Image.new("RGB", (width, height), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    
    # 绘制深灰蓝到深灰色的优雅渐变背景
    for y in range(height):
        ratio = y / height
        r = int(15 * (1 - ratio) + 2 * ratio)
        g = int(23 * (1 - ratio) + 4 * ratio)
        b = int(42 * (1 - ratio) + 8 * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
        
    font_title_size = max(36, int(width * 0.055))
    font_creator_size = max(24, int(width * 0.040))
    
    font_title = _get_font(font_title_size)
    font_creator = _get_font(font_creator_size)
    
    title_text = f"《{title}》"
    creator_text = f"{creator or '无名创作者'} 作品"
    
    try:
        bbox_t = draw.textbbox((0, 0), title_text, font=font_title)
        t_w = bbox_t[2] - bbox_t[0]
        t_h = bbox_t[3] - bbox_t[1]
    except AttributeError:
        t_w, t_h = draw.textsize(title_text, font=font_title)
        
    try:
        bbox_c = draw.textbbox((0, 0), creator_text, font=font_creator)
        c_w = bbox_c[2] - bbox_c[0]
        c_h = bbox_c[3] - bbox_c[1]
    except AttributeError:
        c_w, c_h = draw.textsize(creator_text, font=font_creator)
        
    title_x = (width - t_w) // 2
    title_y = int(height * 0.4)
    
    creator_x = (width - c_w) // 2
    creator_y = title_y + t_h + int(height * 0.1)
    
    draw.text((title_x, title_y), title_text, fill=(255, 255, 255), font=font_title)
    draw.text((creator_x, creator_y), creator_text, fill=(226, 232, 240), font=font_creator)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG")


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

    style = story.get("style", "温暖童趣的手绘绘本")
    
    # 1. 循环生成各角色的标准参考图，并在图上印上对应的名字
    character_paths: list[Path] = []
    for idx, char in enumerate(characters, 1):
        name = char.get("name", f"角色_{idx}")
        subject_type = str(char.get("subject_type", "object")).strip().lower()
        non_human_guard = ""
        if subject_type != "person":
            non_human_guard = (
                f"主角类型是 {subject_type}，主角就是这个主体本身。"
                "不要添加人类头部、身体或操作者，不要把它改造成穿着该物体的人，也不要新增人类主角。"
                "画面中不得出现任何人类、儿童、人形角色、人脸或人手。"
            )
            
        char_img_path = paths["images"] / f"角色参考_{idx}.jpg"
        if force and scene is None and char_img_path.exists():
            char_img_path.unlink()
            
        if not char_img_path.exists():
            prompt = (
                "根据输入的孩子原画制作一张角色标准参考图。"
                f"角色名：{name}。"
                f"外形：{char.get('appearance', '')}。"
                f"特别之处：{char.get('special_ability', '')}。"
                f"画面风格：{style}。"
                f"{non_human_guard}"
                "保留原画最有辨识度的轮廓、颜色、结构和朴拙手绘气质；单一角色完整入镜，"
                "简单浅色背景，竖版3:4，无文字、无字幕、无水印。"
            )
            print(f"正在生成角色【{name}】的标准参考图……")
            _generate_image(prompt=prompt, references=[normalized], output=char_img_path, config=config)
            
            try:
                _add_name_to_image(char_img_path, name)
                print(f"已在角色【{name}】参考图上印写名字")
            except Exception as err:
                print(f"在图片上印写角色【{name}】的名字失败：{err}")
                
        character_paths.append(char_img_path)

    # 2. 场景图片生成
    selected = {scene} if scene else {1, 2, 3, 4}
    outputs: list[Path] = list(character_paths)
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
                "画面中不得出现任何人类、儿童、人形角色、人脸或人手。"
            )
            
        prompt = (
            f"图1是孩子原画。{ref_descr}请生成包含上述角色的故事场景，"
            "严格保留各个角色的辨识度、主要颜色、结构 and 手绘气质，不要重新设计角色。"
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
