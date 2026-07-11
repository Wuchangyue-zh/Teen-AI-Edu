from __future__ import annotations

from pathlib import Path
import docx
from docx.shared import Inches
from .common import load_json, update_manifest

def generate_initial_docx(project_dir: Path, story_path: Path, output_docx_path: Path) -> Path:
    story = load_json(story_path)
    doc = docx.Document()
    
    doc.add_heading(story.get("title", "未命名故事"), 0)
    
    creator = story.get("creator_display", "")
    if creator:
        doc.add_paragraph(f"创作者：{creator}")
    
    doc.add_heading("角色设定", level=1)
    char = story.get("character", {})
    p = doc.add_paragraph()
    p.add_run(f"★ 名字：{char.get('name', '无')}\n")
    p.add_run(f"★ 类型：{char.get('subject_type', '无')}\n")
    p.add_run(f"★ 外貌：{char.get('appearance', '无')}\n")
    p.add_run(f"★ 性格：{char.get('personality', '无')}\n")
    p.add_run(f"★ 特殊能力：{char.get('special_ability', '无')}\n")
    
    doc.add_heading("画面风格", level=1)
    doc.add_paragraph(story.get("style", "无"))
    
    doc.add_heading("故事内容", level=1)
    for scene in story.get("scenes", []):
        idx = scene.get("index", 1)
        doc.add_paragraph(f"--- [ 第 {idx} 幕：{scene.get('title', f'场景 {idx}')} ] ---")
        doc.add_paragraph(f"【旁白】\n{scene.get('narration', '')}")
        doc.add_paragraph(f"【画面提示词】\n{scene.get('visual_prompt', '')}")
        doc.add_paragraph("【配图位置 - 待生成】")
        doc.add_paragraph("")
        
    output_docx_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_docx_path)
    update_manifest(project_dir, "docx_init", [output_docx_path])
    return output_docx_path

def update_docx_with_images(project_dir: Path, story_path: Path, output_docx_path: Path, images_dir: Path) -> Path:
    story = load_json(story_path)
    doc = docx.Document()
    
    doc.add_heading(story.get("title", "未命名故事"), 0)
    
    creator = story.get("creator_display", "")
    if creator:
        doc.add_paragraph(f"创作者：{creator}")
        
    doc.add_heading("角色设定", level=1)
    char = story.get("character", {})
    p = doc.add_paragraph()
    p.add_run(f"★ 名字：{char.get('name', '无')}\n")
    p.add_run(f"★ 类型：{char.get('subject_type', '无')}\n")
    p.add_run(f"★ 外貌：{char.get('appearance', '无')}\n")
    p.add_run(f"★ 性格：{char.get('personality', '无')}\n")
    p.add_run(f"★ 特殊能力：{char.get('special_ability', '无')}\n")
    
    doc.add_heading("画面风格", level=1)
    doc.add_paragraph(story.get("style", "无"))
    
    char_ref = images_dir / "character_reference.jpg"
    if char_ref.exists():
        doc.add_heading("角色标准参考图", level=1)
        doc.add_picture(str(char_ref), width=Inches(3.5))
        
    doc.add_heading("故事内容", level=1)
    for scene in story.get("scenes", []):
        idx = scene.get("index", 1)
        doc.add_paragraph(f"--- [ 第 {idx} 幕：{scene.get('title', f'场景 {idx}')} ] ---")
        doc.add_paragraph(f"【旁白】\n{scene.get('narration', '')}")
        doc.add_paragraph(f"【画面提示词】\n{scene.get('visual_prompt', '')}")
        
        scene_img = images_dir / f"scene_{idx:02d}.jpg"
        if scene_img.exists():
            doc.add_paragraph("【配图】")
            doc.add_picture(str(scene_img), width=Inches(3.5))
        else:
            doc.add_paragraph("【配图位置 - 缺失】")
        doc.add_paragraph("")
        
    output_docx_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_docx_path)
    update_manifest(project_dir, "docx_images", [output_docx_path])
    return output_docx_path
