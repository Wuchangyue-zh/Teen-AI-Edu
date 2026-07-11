import json
import os
import tempfile
import unittest
from pathlib import Path

from 脚本.story_video.common import load_env_file, validate_story
from 脚本.story_video.video import _split_caption_text, _srt_time


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


if __name__ == "__main__":
    unittest.main()
