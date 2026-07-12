import os
import sys
from pathlib import Path

# Add parent directory to sys.path so we can import story_video modules
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from story_video.common import http_json, require_env, load_environment

# Load .env
env_file = Path(__file__).resolve().parents[2] / ".env"
load_environment(env_file)

import base64

MIMO_URL = "https://api.xiaomimimo.com/v1/chat/completions"

def generate_sample(voice_name: str, desc: str, output_path: Path):
    print(f"正在生成预置声音样品：{voice_name} ({desc})...")
    payload = {
        "model": "mimo-v2.5-tts",
        "messages": [
            {"role": "user", "content": "自然、清晰、温暖的讲故事语气。"},
            {"role": "assistant", "content": f"你好，我是小米内置音色{voice_name}。这是我的声音样品，你可以选择我来为你的故事配音哦。"},
        ],
        "audio": {
            "format": "wav",
            "voice": voice_name,
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
        timeout=180,
        retries=2,
    )
    
    audio = ((data.get("choices") or [{}])[0].get("message") or {}).get("audio") or {}
    encoded = audio.get("data")
    if not encoded:
        raise RuntimeError(f"接口没有返回音频数据 ({voice_name})。")
        
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(base64.b64decode(encoded))
    print(f"成功保存到: {output_path}")

def main():
    voices = {
        "冰糖": "小孩女",
        "苏打": "小孩男",
        "茉莉": "成年女",
        "白桦": "成年男"
    }
    
    output_dir = Path(__file__).resolve().parents[2] / "资源" / "官方预置声音"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for voice_name, desc in voices.items():
        output_file = output_dir / f"{voice_name}_{desc}.wav"
        try:
            generate_sample(voice_name, desc, output_file)
        except Exception as e:
            print(f"生成 {voice_name} 失败: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
