from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from .common import (
    ROOT,
    audio_data_uri,
    ensure_project_dirs,
    http_json,
    load_json,
    require_command,
    require_env,
    run_command,
    update_manifest,
)


# 官方合法预置音色（见 参考/03_技术与隐私.md）
OFFICIAL_PRESET_VOICES = {"冰糖", "苏打", "茉莉", "白桦"}
# 表示“使用声音克隆”的模式关键词，这些词不是合法音色名
CLONE_KEYWORDS = {"克隆音", "克隆", "克隆声音", "声音克隆"}
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

    # 文档/命令里指定的音色设定；可能是官方音色名，也可能是“克隆音”这类模式关键词
    voice_setting = (preset_override or story.get("voice") or "").strip()
    clone_requested = voice_setting in CLONE_KEYWORDS

    # 1) 优先使用项目 输入/ 下的个性化声音参考
    source = None
    try:
        source = find_single_input(paths["input"], "声音参考")
    except RuntimeError:
        pass

    # 2) 项目未提供参考，但文档指定“克隆音”时，回退到 Skill 自带的克隆样例
    if source is None and clone_requested:
        bundled_ref = ROOT / "资源" / "用户声音" / "声音参考.wav"
        if bundled_ref.exists():
            source = bundled_ref
            print(f"【声音生成】项目 输入/ 未提供声音参考，但文档指定“克隆音”，改用 Skill 自带样例：{bundled_ref.name}。")
        else:
            print("【声音生成】文档指定“克隆音”，但项目与 Skill 自带样例均无声音参考，将回退到官方预置音色。")

    normalized = None
    preset_voice_name = None
    if source:
        normalized = _normalize_voice(source, paths["work"] / "声音参考_24k.wav")
        print(f"【声音生成】检测到参考声音：{source.name}，启动「声音克隆」模式（模型：mimo-v2.5-tts-voiceclone）。")
    else:
        # 预置音色：绝不能把“克隆音”等模式关键词当作音色名传给接口
        candidate = (
            preset_override
            or story.get("voice")
            or config.get("voice", {}).get("preset_voice", "冰糖")
        )
        if candidate not in OFFICIAL_PRESET_VOICES:
            fallback = config.get("voice", {}).get("preset_voice", "冰糖")
            print(f"【声音生成】“{candidate}”不是有效的官方预置音色，已回退默认音色：{fallback}。")
            candidate = fallback
        preset_voice_name = candidate
        print(f"【声音生成】启动「内置预置音色」模式。所选音色：{preset_voice_name}（模型：mimo-v2.5-tts）。")
    
    selected = {scene} if scene else set(range(1, len(story["scenes"]) + 1))
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

