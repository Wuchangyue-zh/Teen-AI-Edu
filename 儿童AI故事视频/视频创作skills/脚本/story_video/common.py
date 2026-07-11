from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        if key and value and key not in os.environ:
            os.environ[key] = value


def load_environment(explicit_env: Path | None = None) -> None:
    if explicit_env:
        load_env_file(explicit_env)
    load_env_file(ROOT.parent.parent / ".env")
    load_env_file(ROOT.parent / ".env")
    load_env_file(ROOT / ".env")


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"缺少 {name}，请在项目根目录 .env 中配置。")
    return value


def require_command(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"未找到 {name}。请先安装并确保它可以在终端中运行。")
    return path


def run_command(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        stdin=subprocess.DEVNULL,
        text=True,
        capture_output=capture,
    )


def http_json(
    url: str,
    *,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: int,
    retries: int,
) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        request = urllib.request.Request(
            url,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:2000]
            last_error = RuntimeError(f"接口返回 HTTP {exc.code}: {detail}")
            if exc.code not in {408, 429, 500, 502, 503, 504}:
                raise last_error
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
        if attempt < retries:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"接口调用失败，已重试 {retries} 次：{last_error}")


def detect_image_mime(data: bytes) -> str:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    raise RuntimeError("参考图片格式无法识别，请使用 JPG、PNG 或 WEBP。")


def image_data_uri(path: Path) -> str:
    data = path.read_bytes()
    mime = detect_image_mime(data)
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def audio_data_uri(path: Path) -> str:
    data = path.read_bytes()
    suffix = path.suffix.lower()
    mime = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".webm": "audio/webm",
    }.get(suffix, "audio/wav")
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def project_paths(project: Path) -> dict[str, Path]:
    return {
        "root": project,
        "input": project / "input",
        "text": project / "text",
        "images": project / "images",
        "voice": project / "voice",
        "review": project / "review",
        "final": project / "final",
        "work": project / ".work",
    }


def ensure_project_dirs(project: Path) -> dict[str, Path]:
    paths = project_paths(project)
    for key, path in paths.items():
        if key != "root":
            path.mkdir(parents=True, exist_ok=True)
    return paths


def validate_story(story: dict[str, Any]) -> None:
    if not str(story.get("title", "")).strip():
        raise RuntimeError("故事缺少 title。")
    character = story.get("character")
    if not isinstance(character, dict) or not str(character.get("name", "")).strip():
        raise RuntimeError("故事缺少 character.name。")
    if not str(character.get("subject_type", "")).strip():
        raise RuntimeError("故事缺少 character.subject_type。请标记主角是人物、动物、物品、植物、车辆还是建筑。")
    scenes = story.get("scenes")
    if not isinstance(scenes, list) or len(scenes) != 4:
        raise RuntimeError("MVP 故事必须正好包含四幕 scenes。")
    expected = [1, 2, 3, 4]
    actual = [scene.get("index") for scene in scenes]
    if actual != expected:
        raise RuntimeError("四幕场景的 index 必须依次为 1、2、3、4。")
    for scene in scenes:
        if not str(scene.get("narration", "")).strip():
            raise RuntimeError(f"第 {scene['index']} 幕缺少 narration。")
        if not str(scene.get("visual_prompt", "")).strip():
            raise RuntimeError(f"第 {scene['index']} 幕缺少 visual_prompt。")


def update_manifest(project: Path, stage: str, files: list[Path]) -> None:
    manifest_path = project / "run_manifest.json"
    manifest = load_json(manifest_path) if manifest_path.exists() else {"stages": {}}
    manifest.setdefault("stages", {})[stage] = {
        "status": "completed",
        "files": [str(path.relative_to(project)) for path in files if path.exists()],
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_json(manifest_path, manifest)


def ffprobe(path: Path) -> dict[str, Any]:
    require_command("ffprobe")
    result = run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        capture=True,
    )
    return json.loads(result.stdout)
