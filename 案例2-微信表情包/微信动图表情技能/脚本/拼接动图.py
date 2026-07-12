#!/usr/bin/env python3
"""切开规则连环分镜，并导出纯白背景的微信 GIF 表情。"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

目标边长 = 240
最大字节数 = 500 * 1024
白色 = (255, 255, 255)


def 读取参数():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--rows", type=int, required=True)
    parser.add_argument("--cols", type=int, required=True)
    parser.add_argument("--gutter", type=int, default=0, help="每格四边裁去的像素，用于去掉分隔线")
    parser.add_argument("--durations", required=True, help="每格时长（毫秒），以英文逗号分隔")
    parser.add_argument("--target-size", type=int, default=目标边长)
    parser.add_argument("--max-bytes", type=int, default=最大字节数)
    return parser.parse_args()


def 保存动作预览图(帧列表, 路径: Path):
    缩略边长 = 120
    预览 = Image.new("RGB", (缩略边长 * len(帧列表), 缩略边长), 白色)
    for 序号, 帧 in enumerate(帧列表):
        缩略图 = 帧.copy()
        缩略图.thumbnail((缩略边长, 缩略边长), Image.Resampling.LANCZOS)
        x = 序号 * 缩略边长 + (缩略边长 - 缩略图.width) // 2
        y = (缩略边长 - 缩略图.height) // 2
        预览.paste(缩略图, (x, y))
        ImageDraw.Draw(预览).text((序号 * 缩略边长 + 5, 5), str(序号 + 1), fill="#333333")
    预览.save(路径)


def 导出一次(帧列表, 时长列表, 路径: Path, 边长: int, 色彩数: int, 抽帧间隔: int):
    选择帧 = 帧列表[::抽帧间隔]
    选择时长 = [sum(时长列表[i:i + 抽帧间隔]) for i in range(0, len(时长列表), 抽帧间隔)]
    调色板帧 = []
    for 帧 in 选择帧:
        画布 = Image.new("RGB", (边长, 边长), 白色)
        缩放帧 = 帧.copy()
        缩放帧.thumbnail((边长, 边长), Image.Resampling.LANCZOS)
        画布.paste(缩放帧, ((边长 - 缩放帧.width) // 2, (边长 - 缩放帧.height) // 2))
        调色板帧.append(画布.convert("P", palette=Image.Palette.ADAPTIVE, colors=色彩数))
    调色板帧[0].save(路径, save_all=True, append_images=调色板帧[1:], duration=选择时长,
                      loop=0, disposal=2, optimize=True)
    return {"尺寸": 边长, "色彩数": 色彩数, "抽帧间隔": 抽帧间隔,
            "文件字节数": 路径.stat().st_size, "帧数": len(调色板帧)}


def main():
    参数 = 读取参数()
    if 参数.rows < 1 or 参数.cols < 1 or 参数.gutter < 0:
        raise SystemExit("行数、列数必须为正数，分隔线宽度不能为负数")
    时长列表 = [int(value) for value in 参数.durations.split(",")]
    预期帧数 = 参数.rows * 参数.cols
    if len(时长列表) != 预期帧数 or any(value < 20 for value in 时长列表):
        raise SystemExit(f"请提供 {预期帧数} 个时长，每个至少 20 毫秒")
    项目 = 参数.project
    原始素材, 分帧图片, 最终成品, 质检报告 = (项目 / 名称 for 名称 in ("原始素材", "分帧图片", "最终成品", "质检报告"))
    for 文件夹 in (原始素材, 分帧图片, 最终成品, 质检报告):
        文件夹.mkdir(parents=True, exist_ok=True)
    分镜路径 = 原始素材 / "连环分镜.png"
    if 参数.source.resolve() != 分镜路径.resolve():
        shutil.copy2(参数.source, 分镜路径)
    分镜 = Image.open(分镜路径).convert("RGB")
    格宽, 格高 = 分镜.width // 参数.cols, 分镜.height // 参数.rows
    if 格宽 * 参数.cols != 分镜.width or 格高 * 参数.rows != 分镜.height:
        raise SystemExit("原始分镜的宽高必须能被行数和列数整除")
    原始帧 = []
    for 序号 in range(预期帧数):
        行, 列 = divmod(序号, 参数.cols)
        左, 上 = 列 * 格宽 + 参数.gutter, 行 * 格高 + 参数.gutter
        右, 下 = (列 + 1) * 格宽 - 参数.gutter, (行 + 1) * 格高 - 参数.gutter
        if 右 <= 左 or 下 <= 上:
            raise SystemExit("分隔线宽度过大，已经挤掉了画格")
        原始帧.append(分镜.crop((左, 上, 右, 下)))
    # 白色背景本身就是画面的一部分。统一裁切整格可锁定人物位置和比例，避免动画跳动。
    帧列表 = 原始帧
    for 序号, 帧 in enumerate(帧列表):
        帧.save(分帧图片 / f"第{序号 + 1:02d}帧.png")
    保存动作预览图(帧列表, 质检报告 / "动作预览图.png")
    成品路径 = 最终成品 / f"{项目.name}.gif"
    首帧 = Image.new("RGB", (参数.target_size, 参数.target_size), 白色)
    首帧内容 = 帧列表[0].copy()
    首帧内容.thumbnail((参数.target_size, 参数.target_size), Image.Resampling.LANCZOS)
    首帧.paste(首帧内容, ((参数.target_size - 首帧内容.width) // 2, (参数.target_size - 首帧内容.height) // 2))
    首帧.save(最终成品 / "首帧预览.png")
    尝试记录 = []
    for 边长 in (参数.target_size, 220, 200, 180):
        for 色彩数 in (128, 96, 64, 48, 32):
            for 抽帧间隔 in (1, 2):
                尝试 = 导出一次(帧列表, 时长列表, 成品路径, 边长, 色彩数, 抽帧间隔)
                尝试记录.append(尝试)
                if 尝试["文件字节数"] <= 参数.max_bytes:
                    动图 = Image.open(成品路径).convert("RGB")
                    四角 = [动图.getpixel((x, y)) for x, y in ((0, 0), (动图.width - 1, 0), (0, 动图.height - 1), (动图.width - 1, 动图.height - 1))]
                    白底通过 = all(max(abs(c - 255) for c in 像素) <= 8 for 像素 in 四角)
                    报告 = {"是否通过": 白底通过, "格式": "GIF", "尺寸": [动图.width, 动图.height],
                            "帧数": getattr(Image.open(成品路径), "n_frames", 1), "总时长毫秒": sum(时长列表),
                            "文件字节数": 成品路径.stat().st_size, "最大允许字节数": 参数.max_bytes,
                            "背景检查": "白色背景通过" if 白底通过 else "白色背景失败",
                            "导出尝试": 尝试记录, "分镜来源": str(分镜路径)}
                    (质检报告 / "质量检查.json").write_text(json.dumps(报告, ensure_ascii=False, indent=2), encoding="utf-8")
                    if not 白底通过:
                        raise SystemExit(json.dumps(报告, ensure_ascii=False))
                    print(json.dumps(报告, ensure_ascii=False))
                    return
    报告 = {"是否通过": False, "原因": "无法压缩到文件体积限制以内", "导出尝试": 尝试记录}
    (质检报告 / "质量检查.json").write_text(json.dumps(报告, ensure_ascii=False, indent=2), encoding="utf-8")
    raise SystemExit(json.dumps(报告, ensure_ascii=False))


if __name__ == "__main__":
    main()
