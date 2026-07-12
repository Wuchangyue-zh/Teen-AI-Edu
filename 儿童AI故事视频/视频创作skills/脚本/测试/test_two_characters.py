import os
import sys
import shutil
from pathlib import Path

# Add parent directory to sys.path so we can import story_video modules
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from story_video.common import load_json, save_json, ensure_project_dirs
from story_video.docx_helper import generate_initial_docx, parse_docx_to_story, update_docx_with_images
from story_video.images import _add_name_to_image

def test_docx_flow(project_dir: Path):
    print("--- 步骤 1: 验证 DOCX 生成与解析流 ---")
    
    # 模拟包含双角色的故事 JSON
    mock_story = {
        "title": "北宋双雄：苏轼与王安石的相遇",
        "creator_display": "AI 测试员",
        "voice": "苏打",
        "characters": [
            {
                "name": "苏轼",
                "subject_type": "person",
                "appearance": "戴着东坡帽，胡须飘飘，面带微笑的古装文人",
                "personality": "豁达豪放、风趣幽默",
                "special_ability": "吟诗作对、做东坡肉"
            },
            {
                "name": "王安石",
                "subject_type": "person",
                "appearance": "身穿红袍朝服，表情严肃，手握奏折的古装官员",
                "personality": "倔强执着、严谨求实",
                "special_ability": "锐意改革、作诗推敲"
            }
        ],
        "style": "温暖典雅的水墨绘本风格",
        "scenes": [
            {
                "index": 1,
                "title": "汴梁初识",
                "narration": "在繁华的汴梁城，苏轼与王安石在书院相遇了。他们一见如故，开始吟诗作赋。",
                "visual_prompt": "汴梁街头，两位古装文人（苏轼与王安石）坐在茶馆里举杯，周围有竹林背景，水墨古风"
            }
        ]
    }
    
    # 创建模拟项目结构
    paths = ensure_project_dirs(project_dir)
    story_json_path = paths["text"] / "故事.json"
    save_json(story_json_path, mock_story)
    
    # 1. 生成初始 docx
    docx_path = project_dir / "故事.docx"
    if docx_path.exists():
        docx_path.unlink()
    generate_initial_docx(project_dir, story_json_path, docx_path)
    print(f"成功生成初始 docx: {docx_path}")
    
    # 2. 从 docx 解析回 story json
    parsed_story = parse_docx_to_story(docx_path)
    print("解析出来的故事数据：")
    print(f"  - 标题: {parsed_story.get('title')}")
    print(f"  - 创作者: {parsed_story.get('creator_display')}")
    print(f"  - 配音音色: {parsed_story.get('voice')}")
    print(f"  - 角色数: {len(parsed_story.get('characters', []))}")
    for idx, char in enumerate(parsed_story.get('characters', []), 1):
        print(f"    * 角色 {idx}: 名字={char.get('name')}, 类型={char.get('subject_type')}, 外貌={char.get('appearance')}")
        
    # 断言校验
    assert parsed_story.get("voice") == "苏打", "配音解析错误！"
    assert len(parsed_story.get("characters", [])) == 2, "双角色解析错误，数量不为2！"
    assert parsed_story["characters"][0]["name"] == "苏轼", "角色一解析错误！"
    assert parsed_story["characters"][1]["name"] == "王安石", "角色二解析错误！"
    print(">>> 步骤 1 (DOCX 解析与还原测试) 通过！")

def test_name_overlay(project_dir: Path):
    print("\n--- 步骤 2: 验证 PIL 名字标签印写效果 ---")
    from PIL import Image
    
    # 创建一个临时纯色图像作为画板
    test_img_path = project_dir / "temp_char_image.jpg"
    img = Image.new("RGB", (1728, 2304), color=(135, 206, 235)) # 天蓝色背景，模拟 3:4 分辨率
    img.save(test_img_path)
    
    # 调用印写名字函数
    _add_name_to_image(test_img_path, "苏轼")
    print(f"已生成带名字标签的临时图: {test_img_path}")
    
    # 校验文件存在性
    assert test_img_path.exists(), "名字图片生成失败！"
    
    # 尝试再次打开，确保没有损坏 JPEG 结构
    img_check = Image.open(test_img_path)
    print(f"名字图片校验通过，尺寸: {img_check.size}")
    img_check.close()
    
    # 移动到图片目录作为角色参考之一用于预览
    char_ref_path = project_dir / "图片" / "角色参考_1.jpg"
    char_ref_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(test_img_path, char_ref_path)
    
    # 为王安石也做一个参考图
    char_ref_path2 = project_dir / "图片" / "角色参考_2.jpg"
    img2 = Image.new("RGB", (1728, 2304), color=(255, 182, 193)) # 粉色背景
    img2.save(test_img_path)
    _add_name_to_image(test_img_path, "王安石")
    shutil.copy2(test_img_path, char_ref_path2)
    
    # 试着更新 docx，把这些带名字的标准图插入
    story_json_path = project_dir / ".工作" / "故事.json"
    docx_path = project_dir / "故事.docx"
    images_dir = project_dir / "图片"
    update_docx_with_images(project_dir, story_json_path, docx_path, images_dir)
    print("已成功将带角色名字的参考图插入故事文档！")
    print(">>> 步骤 2 (姓名标印与文档同步测试) 通过！")

def main():
    mock_proj = Path(__file__).resolve().parents[2] / "脚本" / "测试" / "mock_project"
    mock_proj.mkdir(parents=True, exist_ok=True)
    try:
        test_docx_flow(mock_proj)
        test_name_overlay(mock_proj)
        print("\n🎉 全部单元测试通过！两个角色独立设定及名字标印功能正常运作。")
    finally:
        # 清理测试文件夹
        if mock_proj.exists():
            shutil.rmtree(mock_proj)

if __name__ == "__main__":
    main()
