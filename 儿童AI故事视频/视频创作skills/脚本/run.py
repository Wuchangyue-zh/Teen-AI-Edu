#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from story_video.common import ROOT, load_environment, load_json, require_command
from story_video.images import generate_images
from story_video.project import initialize_project
from story_video.verify import verify_project
from story_video.video import render_video
from story_video.voice import generate_voice
from story_video.docx_helper import generate_initial_docx, update_docx_with_images


def resolve_path(value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    if (ROOT / path).exists():
        return ROOT / path
    parts = path.parts
    if parts and parts[0] == "output":
        path = Path(*parts[1:])
    return ROOT.parent / path


def load_config(path: Path) -> dict:
    if not path.exists():
        raise RuntimeError(f"找不到配置文件：{path}")
    return load_json(path)


def preflight(config: dict) -> bool:
    statuses = []
    print("儿童 AI 故事视频 - 环境检查")
    print(f"Python: {sys.version.split()[0]}")
    for command in ("ffmpeg", "ffprobe"):
        found = shutil.which(command)
        statuses.append(bool(found))
        print(f"{command}: {'已安装' if found else '缺失'}")
    for key in ("VOLCENGINE_API_KEY", "MIMO_API_KEY"):
        configured = bool(os.environ.get(key, "").strip())
        statuses.append(configured)
        print(f"{key}: {'已配置' if configured else '缺失'}")
    width = int(config["image"]["width"])
    height = int(config["image"]["height"])
    size_ok = width * height >= 3_686_400 and width * 4 == height * 3
    statuses.append(size_ok)
    print(f"豆包图片尺寸: {width}x{height} ({'通过' if size_ok else '不符合3:4或最低像素要求'})")
    video = config["video"]
    ratio_ok = int(video["width"]) * 4 == int(video["height"]) * 3
    statuses.append(ratio_ok)
    print(f"最终视频尺寸: {video['width']}x{video['height']} ({'通过' if ratio_ok else '不是3:4'})")
    passed = all(statuses)
    print("检查结果：" + ("可以开始制作。" if passed else "请先补齐以上缺失项。"))
    return passed


def add_project_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", required=True, help="项目目录，例如 output/小小创作者001")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="从孩子原画自动生成3:4故事视频")
    parser.add_argument("--config", default=str(ROOT / "config.json"), help="配置文件路径")
    parser.add_argument("--env-file", help="可选的 .env 路径")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("preflight", help="检查环境、密钥和默认尺寸")

    init = sub.add_parser("init", help="建立一个新的故事项目")
    add_project_argument(init)
    init.add_argument("--drawing", required=True, help="孩子原画路径")
    init.add_argument("--story", required=True, help="四幕故事 JSON 路径")
    init.add_argument("--voice", help="15-30秒参考声音路径；只做图片时可暂不提供")

    images = sub.add_parser("images", help="生成角色标准图和四幕故事配图")
    add_project_argument(images)
    images.add_argument("--scene", type=int, choices=range(1, 5), help="只处理指定场景")
    images.add_argument("--force", action="store_true", help="覆盖已有结果")

    voice = sub.add_parser("voice", help="使用小米 MiMo 克隆参考声音")
    add_project_argument(voice)
    voice.add_argument("--scene", type=int, choices=range(1, 5), help="只处理指定场景")
    voice.add_argument("--force", action="store_true", help="覆盖已有结果")

    render = sub.add_parser("render", help="合成3:4 MP4并生成字幕")
    add_project_argument(render)
    render.add_argument("--bgm", help="指定背景音乐，可以是文件名（如 卡农.mp3）或路径")
    render.add_argument("--force", action="store_true", help="覆盖已有结果")

    verify = sub.add_parser("verify", help="检查最终文件是否完整兼容")
    add_project_argument(verify)

    docx_cmd = sub.add_parser("docx", help="生成或更新故事 DOCX 文档")
    add_project_argument(docx_cmd)

    all_cmd = sub.add_parser("all", help="初始化并执行全部制作步骤")
    add_project_argument(all_cmd)
    all_cmd.add_argument("--drawing", required=True, help="孩子原画路径")
    all_cmd.add_argument("--story", required=True, help="四幕故事 JSON 路径")
    all_cmd.add_argument("--voice", required=True, help="15-30秒参考声音路径")
    all_cmd.add_argument("--bgm", help="指定背景音乐，可以是文件名（如 卡农.mp3）或路径")
    all_cmd.add_argument("--force", action="store_true", help="覆盖已有结果")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    load_environment(resolve_path(args.env_file) if args.env_file else None)
    config = load_config(resolve_path(args.config))
    try:
        if args.command == "preflight":
            return 0 if preflight(config) else 1
        project = resolve_path(args.project)
        if args.command in {"init", "all"}:
            initialize_project(
                project,
                drawing=resolve_path(args.drawing),
                story_path=resolve_path(args.story),
                voice=resolve_path(args.voice) if args.voice else None,
                config=config,
            )
            story_path = project / ".工作" / "故事.json"
            docx_path = project / "故事.docx"
            generate_initial_docx(project, story_path, docx_path)
            print(f"项目已建立且故事文档已初始化：{project}")
        if args.command == "docx":
            story_path = project / ".工作" / "故事.json"
            docx_path = project / "故事.docx"
            generate_initial_docx(project, story_path, docx_path)
            print(f"故事文档已初始化：{docx_path}")
        if args.command in {"images", "all"}:
            generate_images(
                project,
                config=config,
                scene=getattr(args, "scene", None),
                force=getattr(args, "force", False),
            )
            story_path = project / ".工作" / "故事.json"
            docx_path = project / "故事.docx"
            images_dir = project / "图片"
            if story_path.exists():
                update_docx_with_images(project, story_path, docx_path, images_dir)
                print(f"故事文档已更新插入图片：{docx_path}")
        if args.command in {"voice", "all"}:
            generate_voice(
                project,
                config=config,
                scene=getattr(args, "scene", None),
                force=getattr(args, "force", False),
            )
        if args.command in {"render", "all"}:
            final = render_video(
                project,
                config=config,
                force=getattr(args, "force", False),
                bgm=getattr(args, "bgm", None),
            )
            print(f"视频已生成：{final}")
        if args.command in {"verify", "all"}:
            report = verify_project(project, config=config)
            for name, passed in report["checks"].items():
                print(f"{'通过' if passed else '未通过'}：{name}")
            if not report["passed"]:
                return 2
            if config.get("privacy", {}).get("delete_normalized_voice_after_success", True):
                normalized = project / ".工作" / "声音参考_24k.wav"
                if normalized.exists():
                    normalized.unlink()
            print("全部检查通过，可以交付。")
        return 0
    except Exception as exc:
        print(f"制作失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

