from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from .common import (
    audio_data_uri,
    ensure_project_dirs,
    http_json,
    load_json,
    require_command,
    require_env,
    run_command,
    update_manifest,
)
from .project import find_single_input


MIMO_URL = "https://api.xiaomimimo.com/v1/chat/completions"


def _normalize_voice(source: Path, target: Path) -> Path:
    if target.exists():
        return target
    require_command("ffmpeg")
    run_command([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(source), "-vn", "-ac", "1", "-ar", "24000",
        "-c:a", "pcm_s16le", str(target),
    ])
    return target


def _synthesize(
    *,
    text: str,
    reference: Path | None,
    preset_voice: str | None,
    output: Path,
    config: dict[str, Any],
) -> Path:
    voice_config = config["voice"]
    
    if reference:
        payload = {
            "model": "mimo-v2.5-tts-voiceclone",
            "messages": [
                {"role": "user", "content": voice_config.get("instruction", "自然的中文讲故事语气。")},
                {"role": "assistant", "content": text},
            ],
            "audio": {
                "format": voice_config.get("format", "wav"),
                "voice": audio_data_uri(reference),
            },
            "stream": False,
        }
    else:
        payload = {
            "model": "mimo-v2.5-tts",
            "messages": [
                {"role": "user", "content": voice_config.get("instruction", "自然的中文讲故事语气。")},
                {"role": "assistant", "content": text},
            ],
            "audio": {
                "format": voice_config.get("format", "wav"),
                "voice": preset_voice or "冰糖",
            },
            "stream": False,
        }

    data = http_json(
        MIMO_URL,
        payload=payload,
        headers={
            "api-key": require_env("MIMO_API_KEY"),
            "Content-Type": "application/json",
        },
        timeout=int(voice_config.get("timeout_seconds", 180)),
        retries=int(voice_config.get("max_retries", 2)),
    )
    audio = ((data.get("choices") or [{}])[0].get("message") or {}).get("audio") or {}
    encoded = audio.get("data")
    if not encoded:
        raise RuntimeError("小米 MiMo 接口没有返回音频。")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(base64.b64decode(encoded))
    return output


def generate_voice(
    project: Path,
    *,
    config: dict[str, Any],
    scene: int | None = None,
    force: bool = False,
    preset_override: str | None = None,
) -> list[Path]:
    from .docx_helper import sync_docx_to_json
    sync_docx_to_json(project)
    paths = ensure_project_dirs(project)
    story = load_json(paths["text"] / "故事.json")
    source = None
    try:
        source = find_single_input(paths["input"], "声音参考")
    except RuntimeError:
        pass

    normalized = None
    preset_voice_name = None
    if source:
        normalized = _normalize_voice(source, paths["work"] / "声音参考_24k.wav")
        print(f"【声音生成】检测到个性化参考声音：{source.name}，启动「声音克隆」模式（模型：mimo-v2.5-tts-voiceclone）。")
    else:
        preset_voice_name = (
            preset_override 
            or story.get("voice") 
            or config.get("voice", {}).get("preset_voice", "冰糖")
        )
        print(f"【声音生成】未检测到个性化参考声音，启动「内置预置音色」模式。所选音色：{preset_voice_name}（模型：mimo-v2.5-tts）。")
    
    selected = {scene} if scene else {1, 2, 3, 4}
    outputs: list[Path] = []
    for scene_data in story["scenes"]:
        index = int(scene_data["index"])
        output = paths["voice"] / f"场景_{index:02d}.wav"
        if index not in selected:
            if output.exists():
                outputs.append(output)
            continue
        if output.exists() and not force:
            print(f"第 {index} 幕旁白已存在，跳过。")
            outputs.append(output)
            continue
        print(f"正在生成第 {index} 幕旁白……")
        _synthesize(
            text=scene_data["narration"],
            reference=normalized,
            preset_voice=preset_voice_name,
            output=output,
            config=config,
        )
        outputs.append(output)
    update_manifest(project, "voice", outputs)
    return outputs

