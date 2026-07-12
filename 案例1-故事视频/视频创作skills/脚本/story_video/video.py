from __future__ import annotations

import shutil
import re
from pathlib import Path
from typing import Any

from .common import ensure_project_dirs, ffprobe, load_json, require_command, run_command, update_manifest


def _audio_duration(path: Path) -> float:
    data = ffprobe(path)
    return float(data.get("format", {}).get("duration") or 0.0)


def _srt_time(seconds: float) -> str:
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _split_caption_text(text: str, max_chars: int = 16) -> list[str]:
    pieces = [part.strip() for part in re.findall(r"[^，。！？!?；;,.]+[，。！？!?；;,.]?", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if current and len(current) + len(piece) <= max_chars:
            current += piece
            continue
        if current:
            chunks.append(current)
        current = piece
    if current:
        chunks.append(current)
    return chunks or [text]


def _write_srt(
    story: dict[str, Any],
    audio_paths: list[Path],
    output: Path,
    *,
    max_chars: int,
) -> Path:
    cursor = 0.0
    blocks: list[str] = []
    number = 1
    for scene, audio in zip(story["scenes"], audio_paths):
        duration = _audio_duration(audio)
        chunks = _split_caption_text(scene["narration"], max_chars=max_chars)
        weights = [max(1, len(re.sub(r"[，。！？!?；;,.]", "", chunk))) for chunk in chunks]
        total_weight = sum(weights)
        scene_end = cursor + duration
        for index, (chunk, weight) in enumerate(zip(chunks, weights)):
            chunk_end = scene_end if index == len(chunks) - 1 else cursor + duration * weight / total_weight
            blocks.append(
                f"{number}\n{_srt_time(cursor)} --> {_srt_time(chunk_end)}\n{chunk}\n"
            )
            cursor = chunk_end
            duration = max(0.0, scene_end - cursor)
            total_weight -= weight
            number += 1
    output.write_text("\n".join(blocks), encoding="utf-8")
    return output


def _has_subtitles_filter() -> bool:
    result = run_command(["ffmpeg", "-hide_banner", "-filters"], capture=True)
    return " subtitles " in result.stdout or " subtitles " in result.stderr


def _resolve_bgm_path(bgm_name: str, config: dict[str, Any]) -> Path | None:
    p = Path(bgm_name)
    if p.exists() and p.is_file():
        return p
    
    from .common import ROOT
    bgm_dir = ROOT / "资源" / "背景音乐"
    if bgm_dir.exists():
        p = bgm_dir / bgm_name
        if p.exists() and p.is_file():
            return p
        for ext in (".mp3", ".wav"):
            p = bgm_dir / f"{bgm_name}{ext}"
            if p.exists() and p.is_file():
                return p
            
    mappings = config.get("video", {}).get("bgm_mappings", {})
    if bgm_name in mappings:
        mapped_name = mappings[bgm_name]
        return _resolve_bgm_path(mapped_name, config)
        
    return None


def _detect_bgm_from_story(story: dict[str, Any], config: dict[str, Any]) -> Path | None:
    style_text = story.get("style", "")
    title_text = story.get("title", "")
    content_to_check = f"{title_text} {style_text}"
    
    mappings = config.get("video", {}).get("bgm_mappings", {})
    for keyword, filename in mappings.items():
        if keyword in content_to_check:
            resolved = _resolve_bgm_path(filename, config)
            if resolved:
                return resolved
                
    fallback_keys = ["温暖", "温柔", "卡农"]
    for key in fallback_keys:
        if key in mappings:
            resolved = _resolve_bgm_path(mappings[key], config)
            if resolved:
                return resolved
                
    from .common import ROOT
    bgm_dir = ROOT / "资源" / "背景音乐"
    if bgm_dir.exists():
        files = list(bgm_dir.glob("*.mp3")) + list(bgm_dir.glob("*.wav"))
        if files:
            return files[0]
            
    return None


def _is_bgm_disabled(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"无", "关闭", "none", "off", "no"}


def render_video(
    project: Path,
    *,
    config: dict[str, Any],
    force: bool = False,
    bgm: str | None = None,
) -> Path:
    from .docx_helper import sync_docx_to_json
    sync_docx_to_json(project)
    require_command("ffmpeg")
    paths = ensure_project_dirs(project)
    story = load_json(paths["text"] / "故事.json")
    video_config = config["video"]
    width = int(video_config["width"])
    height = int(video_config["height"])
    fps = int(video_config.get("fps", 15))
    crf = int(video_config.get("crf", 21))

    scene_count = len(story["scenes"])
    image_paths = [paths["images"] / f"场景_{index:02d}.jpg" for index in range(1, scene_count + 1)]
    audio_paths = [paths["voice"] / f"场景_{index:02d}.wav" for index in range(1, scene_count + 1)]
    missing = [path for path in image_paths + audio_paths if not path.exists()]
    if missing:
        raise RuntimeError("合成前素材不完整：" + "、".join(str(path.name) for path in missing))

    final = paths["final"] / "故事视频.mp4"
    if final.exists() and not force:
        print("最终视频已存在，跳过合成。")
        return final

    clips: list[Path] = []
    for index, (image, audio) in enumerate(zip(image_paths, audio_paths), 1):
        duration = _audio_duration(audio)
        if duration <= 0:
            raise RuntimeError(f"第 {index} 幕音频时长无效。")
        clip = paths["work"] / f"片段_{index:02d}.mp4"
        fade_out_start = max(0.0, duration - 0.35)
        video_filter = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase:in_range=full:out_range=tv,"
            f"crop={width}:{height},"
            f"fade=t=in:st=0:d=0.25,fade=t=out:st={fade_out_start:.3f}:d=0.25,"
            "format=yuv420p,setsar=1"
        )
        run_command([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-loop", "1", "-i", str(image), "-i", str(audio),
            "-vf", video_filter,
            "-t", f"{duration:.3f}", "-r", str(fps),
            "-c:v", "libx264", "-preset", "fast", "-crf", str(crf),
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-shortest",
            "-movflags", "+faststart", str(clip),
        ])
        clips.append(clip)

    ending_image = paths["images"] / "结尾页.jpg"
    ending_duration = float(video_config.get("ending_duration_seconds", 2.8))
    if ending_image.exists():
        print("正在将故事结尾作品页合入视频中...")
        ending_audio = paths["work"] / "结尾_silent.wav"
        run_command([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-t", f"{ending_duration:.3f}", str(ending_audio)
        ])
        
        ending_clip = paths["work"] / f"片段_{scene_count + 1:02d}.mp4"
        ending_video_filter = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase:in_range=full:out_range=tv,"
            f"crop={width}:{height},"
            f"fade=t=in:st=0:d=0.35,fade=t=out:st={max(0.0, ending_duration - 0.45):.3f}:d=0.45,"
            "format=yuv420p,setsar=1"
        )
        run_command([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-loop", "1", "-i", str(ending_image), "-i", str(ending_audio),
            "-vf", ending_video_filter,
            "-t", f"{ending_duration:.3f}", "-r", str(fps),
            "-c:v", "libx264", "-preset", "fast", "-crf", str(crf),
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-shortest",
            "-movflags", "+faststart", str(ending_clip),
        ])
        clips.append(ending_clip)

    concat_file = paths["work"] / "片段列表.txt"
    concat_file.write_text(
        "\n".join(f"file '{path.as_posix().replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'" for path in clips) + "\n",
        encoding="utf-8",
    )
    no_subtitles = paths["work"] / "故事_无字幕.mp4"
    run_command([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy", "-movflags", "+faststart", str(no_subtitles),
    ])

    bgm_enabled = bool(video_config.get("bgm_enabled", True))
    bgm_file: Path | None = None
    if bgm_enabled and not _is_bgm_disabled(bgm or story.get("bgm")):
        if bgm:
            bgm_file = _resolve_bgm_path(bgm, config)
        elif story.get("bgm") and story.get("bgm") != "自动匹配":
            bgm_file = _resolve_bgm_path(story["bgm"], config)
        else:
            bgm_file = _detect_bgm_from_story(story, config)

    if bgm_file:
        try:
            print(f"应用背景音乐：{bgm_file.name}")
            total_duration = sum(_audio_duration(audio) for audio in audio_paths)
            if ending_image.exists():
                total_duration += ending_duration
            bgm_volume = float(video_config.get("bgm_volume", 0.12))
            
            fade_duration = 1.5
            fade_start = max(0.0, total_duration - fade_duration)
            
            mixed_video = paths["work"] / "故事_混音.mp4"
            
            audio_filter = (
                f"[1:a]volume={bgm_volume},afade=t=out:st={fade_start:.3f}:d={fade_duration:.3f}[bgm];"
                f"[0:a][bgm]amix=inputs=2:duration=first[a]"
            )
            
            run_command([
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(no_subtitles),
                "-stream_loop", "-1", "-i", str(bgm_file),
                "-filter_complex", audio_filter,
                "-map", "0:v", "-map", "[a]",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "128k",
                str(mixed_video)
            ])
            no_subtitles = mixed_video
        except Exception as e:
            print(f"背景音乐混音失败，跳过背景音乐直接输出。错误详情：{e}")

    srt = _write_srt(
        story,
        audio_paths,
        paths["voice"] / "故事字幕.srt",
        max_chars=int(video_config.get("subtitle_max_chars", 16)),
    )
    burned = bool(video_config.get("burn_subtitles", True)) and _has_subtitles_filter()
    if burned:
        escaped = str(srt.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        font_size = int(video_config.get("subtitle_font_size", 15))
        margin_bottom = int(video_config.get("subtitle_margin_bottom", 50))
        subtitle_filter = (
            f"subtitles=filename='{escaped}':"
            f"force_style='FontName=PingFang SC,FontSize={font_size},PrimaryColour=&H00FFFFFF,"
            f"OutlineColour=&H00000000,BorderStyle=1,Outline=2,Alignment=2,MarginV={margin_bottom}',"
            "scale=in_range=tv:out_range=tv,format=yuv420p"
        )
        try:
            run_command([
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(no_subtitles), "-vf", subtitle_filter,
                "-c:v", "libx264", "-preset", "fast", "-crf", str(crf),
                "-pix_fmt", "yuv420p",
                "-color_range", "tv",
                "-c:a", "copy", "-movflags", "+faststart", str(final),
            ])
        except Exception:
            print("当前 FFmpeg 无法烧录中文字幕，已保留 SRT 并输出无烧录字幕视频。")
            shutil.copy2(no_subtitles, final)
    else:
        shutil.copy2(no_subtitles, final)

    update_manifest(project, "render", [final, srt])
    return final
