from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import ensure_project_dirs, ffprobe, save_json, update_manifest


def verify_project(project: Path, *, config: dict[str, Any]) -> dict[str, Any]:
    paths = ensure_project_dirs(project)
    final = paths["final"] / "故事视频.mp4"
    expected_images = [paths["images"] / f"scene_{index:02d}.jpg" for index in range(1, 5)]
    expected_audio = [paths["voice"] / f"scene_{index:02d}.wav" for index in range(1, 5)]
    checks: dict[str, bool] = {
        "角色标准图存在": (paths["images"] / "character_reference.jpg").exists(),
        "四幕图片齐全": all(path.exists() for path in expected_images),
        "四幕旁白齐全": all(path.exists() for path in expected_audio),
        "故事板存在": (paths["review"] / "故事板.jpg").exists(),
        "最终视频存在": final.exists(),
    }
    details: dict[str, Any] = {}
    if final.exists():
        probe = ffprobe(final)
        streams = probe.get("streams", [])
        video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), {})
        audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), {})
        video_config = config["video"]
        checks.update({
            "视频尺寸正确": (
                int(video_stream.get("width") or 0) == int(video_config["width"])
                and int(video_stream.get("height") or 0) == int(video_config["height"])
            ),
            "视频编码兼容": video_stream.get("codec_name") == "h264",
            "包含音频": bool(audio_stream),
            "像素格式兼容": video_stream.get("pix_fmt") == "yuv420p",
        })
        details = {
            "duration_seconds": float(probe.get("format", {}).get("duration") or 0),
            "size_bytes": int(probe.get("format", {}).get("size") or 0),
            "video_codec": video_stream.get("codec_name"),
            "audio_codec": audio_stream.get("codec_name"),
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "pixel_format": video_stream.get("pix_fmt"),
        }
    passed = all(checks.values())
    report = {"passed": passed, "checks": checks, "video": details}
    report_path = project / "verification.json"
    save_json(report_path, report)
    if passed:
        update_manifest(project, "verify", [report_path])
    return report

