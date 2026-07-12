import json
import os
import subprocess
import sys
import tempfile
import unittest
import io
import zipfile
from pathlib import Path

from 脚本.story_video.common import ensure_project_dirs, load_env_file, save_json, validate_story
from 脚本.story_video.video import _split_caption_text, _srt_time
from 脚本.story_video.docx_helper import generate_initial_docx, parse_docx_to_story, update_docx_with_images
from 脚本.story_video.images import _character_reference_paths, _generate_ending_slide, generate_images
from 脚本.story_video.project import initialize_project


ROOT = Path(__file__).resolve().parents[2]


class StoryContractTests(unittest.TestCase):
    def test_example_story_matches_four_scene_contract(self):
        story = json.loads((ROOT / "参考" / "story.example.json").read_text(encoding="utf-8"))
        validate_story(story)
        self.assertEqual([scene["index"] for scene in story["scenes"]], [1, 2, 3, 4])

    def test_story_requires_exactly_four_scenes(self):
        story = json.loads((ROOT / "参考" / "story.example.json").read_text(encoding="utf-8"))
        story["scenes"] = story["scenes"][:3]
        with self.assertRaisesRegex(RuntimeError, "正好包含四幕"):
            validate_story(story)

    def test_story_requires_subject_type(self):
        story = json.loads((ROOT / "参考" / "story.example.json").read_text(encoding="utf-8"))
        story["character"].pop("subject_type")
        with self.assertRaisesRegex(RuntimeError, "subject_type"):
            validate_story(story)


class EnvironmentTests(unittest.TestCase):
    def test_env_loader_ignores_inline_comment(self):
        with tempfile.TemporaryDirectory() as folder:
            env_path = Path(folder) / ".env"
            env_path.write_text("TEST_CHILD_STORY_KEY=abc123 # 课堂测试\n", encoding="utf-8")
            os.environ.pop("TEST_CHILD_STORY_KEY", None)
            load_env_file(env_path)
            self.assertEqual(os.environ["TEST_CHILD_STORY_KEY"], "abc123")
            os.environ.pop("TEST_CHILD_STORY_KEY", None)


class SubtitleTests(unittest.TestCase):
    def test_srt_time_format(self):
        self.assertEqual(_srt_time(65.432), "00:01:05,432")

    def test_long_narration_is_split_into_short_caption_chunks(self):
        chunks = _split_caption_text(
            "小城门每天守在山脚下。一个晚上，它听见风说，森林里有一颗迷路的小星星。",
            max_chars=16,
        )
        self.assertGreaterEqual(len(chunks), 3)
        self.assertTrue(all(len(chunk) <= 16 for chunk in chunks))


class DocxRefreshTests(unittest.TestCase):
    def _story(self):
        return {
            "title": "署名测试故事",
            "creator_display": "星光创作者",
            "bgm": "卡农",
            "character": {"name": "小灯塔", "subject_type": "building", "appearance": "蓝色灯塔"},
            "scenes": [
                {"index": index, "title": f"第 {index} 幕", "narration": f"这是第 {index} 幕旁白。", "visual_prompt": f"第 {index} 幕画面"}
                for index in range(1, 5)
            ],
        }

    def _embedded_colors(self, docx_path):
        from PIL import Image
        with zipfile.ZipFile(docx_path) as archive:
            media = [name for name in archive.namelist() if name.startswith("word/media/")]
            return [Image.open(io.BytesIO(archive.read(name))).convert("RGB").getpixel((0, 0)) for name in media]

    def test_bgm_round_trip_and_scene_image_refresh(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder) / "项目"
            work, images = project / ".工作", project / "图片"
            work.mkdir(parents=True)
            images.mkdir()
            story_path, docx_path = work / "故事.json", project / "故事.docx"
            story_path.write_text(json.dumps(self._story(), ensure_ascii=False), encoding="utf-8")
            generate_initial_docx(project, story_path, docx_path)
            self.assertEqual(parse_docx_to_story(docx_path)["bgm"], "卡农")

            scene = images / "场景_02.jpg"
            Image.new("RGB", (40, 60), (255, 0, 0)).save(scene)
            update_docx_with_images(project, story_path, docx_path, images)
            self.assertIn((254, 0, 0), self._embedded_colors(docx_path))

            Image.new("RGB", (40, 60), (0, 0, 255)).save(scene)
            update_docx_with_images(project, story_path, docx_path, images)
            self.assertIn((0, 0, 254), self._embedded_colors(docx_path))

    def test_ending_slide_is_created_at_story_ratio(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "ending.jpg"
            _generate_ending_slide("星光故事", "星光创作者", output, {"image": {"width": 360, "height": 480}})
            with Image.open(output) as image:
                self.assertEqual(image.size, (360, 480))

    def test_story_can_initialize_docx_before_original_art_is_available(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder) / "项目"
            source_story = Path(folder) / "故事.json"
            source_story.write_text(json.dumps(self._story(), ensure_ascii=False), encoding="utf-8")
            initialize_project(project, drawing=None, story_path=source_story, voice=None, config={})
            story_path = project / ".工作" / "故事.json"
            docx_path = project / "故事.docx"
            generate_initial_docx(project, story_path, docx_path)
            self.assertTrue(docx_path.exists())
            self.assertFalse(any((project / "输入").glob("原始手绘.*")))


class PrototypeGateTests(unittest.TestCase):
    def test_prototype_command_is_available(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "脚本" / "run.py"), "--help"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("prototype", result.stdout)

    def test_scene_generation_requires_confirmed_prototype(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder) / "项目"
            paths = ensure_project_dirs(project)
            save_json(paths["text"] / "故事.json", DocxRefreshTests()._story())
            Image.new("RGB", (40, 60), (20, 80, 120)).save(paths["input"] / "原始手绘.jpg")
            Image.new("RGB", (40, 60), (20, 80, 120)).save(paths["work"] / "手绘参考.jpg")
            with self.assertRaisesRegex(RuntimeError, "缺少已确认的角色原型"):
                generate_images(project, config={"image": {}}, scene=1)

    def test_reference_paths_match_character_count(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = ensure_project_dirs(Path(folder) / "项目")
            result = _character_reference_paths(paths, [{"name": "甲"}, {"name": "乙"}])
            self.assertEqual([path.name for path in result], ["角色参考_1.jpg", "角色参考_2.jpg"])


if __name__ == "__main__":
    unittest.main()
