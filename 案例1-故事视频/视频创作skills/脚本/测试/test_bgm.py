import unittest
from pathlib import Path
from 脚本.story_video.video import _resolve_bgm_path, _detect_bgm_from_story

class BGMTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "video": {
                "bgm_enabled": True,
                "bgm_volume": 0.12,
                "bgm_mappings": {
                    "开心": "菊次郎的夏天.mp3",
                    "活泼": "菊次郎的夏天.mp3",
                    "搞笑": "菊次郎的夏天.mp3",
                    "幽默": "菊次郎的夏天.mp3",
                    "温暖": "卡农.mp3",
                    "温柔": "卡农.mp3",
                    "温馨": "卡农.mp3",
                    "勇敢": "If - Death Pledge_HQ.mp3",
                    "冒险": "If - Death Pledge_HQ.mp3",
                    "空灵": "空灵之声.mp3",
                    "安静": "卡农.mp3",
                    "静谧": "卡农.mp3",
                    "悲伤": "卡农.mp3",
                    "戏剧": "卡农.mp3"
                }
            }
        }

    def test_resolve_bgm_by_exact_name(self):
        path = _resolve_bgm_path("卡农.mp3", self.config)
        self.assertIsNotNone(path)
        self.assertTrue(path.exists())
        self.assertEqual(path.name, "卡农.mp3")

    def test_resolve_bgm_by_name_without_extension(self):
        path = _resolve_bgm_path("卡农", self.config)
        self.assertIsNotNone(path)
        self.assertEqual(path.name, "卡农.mp3")

    def test_resolve_bgm_by_mapped_keyword(self):
        path = _resolve_bgm_path("开心", self.config)
        self.assertIsNotNone(path)
        self.assertEqual(path.name, "菊次郎的夏天.mp3")

    def test_resolve_invalid_bgm_returns_none(self):
        path = _resolve_bgm_path("non_existent_music_file_xyz", self.config)
        self.assertIsNone(path)

    def test_detect_bgm_from_story_style(self):
        story = {
            "title": "测试故事",
            "style": "这是一个开心和活泼的故事"
        }
        path = _detect_bgm_from_story(story, self.config)
        self.assertIsNotNone(path)
        self.assertEqual(path.name, "菊次郎的夏天.mp3")

    def test_detect_bgm_from_story_title(self):
        story = {
            "title": "勇敢的小城门",
            "style": "普通的画风"
        }
        path = _detect_bgm_from_story(story, self.config)
        self.assertIsNotNone(path)
        self.assertEqual(path.name, "If - Death Pledge_HQ.mp3")

    def test_detect_bgm_fallback(self):
        story = {
            "title": "无匹配故事",
            "style": "水彩画风格"
        }
        path = _detect_bgm_from_story(story, self.config)
        self.assertIsNotNone(path)
        # Should fallback to one of the fallback keys (e.g. 卡农.mp3)
        self.assertEqual(path.name, "卡农.mp3")

if __name__ == "__main__":
    unittest.main()
