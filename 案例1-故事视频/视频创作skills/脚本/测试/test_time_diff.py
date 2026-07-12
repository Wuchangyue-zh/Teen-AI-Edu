import time
import sys
from pathlib import Path

# Add parent directory to sys.path so we can import story_video modules
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from story_video.common import http_json, require_env, load_environment, audio_data_uri

# Load .env
env_file = Path(__file__).resolve().parents[2] / ".env"
load_environment(env_file)

MIMO_URL = "https://api.xiaomimimo.com/v1/chat/completions"

def test_preset():
    print("--- 开始测试官方预置音色 (mimo-v2.5-tts) ---")
    payload = {
        "model": "mimo-v2.5-tts",
        "messages": [
            {"role": "user", "content": "自然、清晰、温暖的讲故事语气，语速稍慢，适合日常故事分享。"},
            {"role": "assistant", "content": "苏轼和王安石是宋代非常有名的文学家，他们曾经是很好的朋友，也写过很多美妙的诗歌。"},
        ],
        "audio": {
            "format": "wav",
            "voice": "冰糖",
        },
        "stream": False,
    }
    
    start_time = time.time()
    try:
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
        end_time = time.time()
        elapsed = end_time - start_time
        choices = data.get("choices") or [{}]
        has_audio = bool(choices[0].get("message", {}).get("audio", {}).get("data"))
        print(f"官方预置音色生成成功！耗时: {elapsed:.2f} 秒 (是否成功返回音频: {has_audio})")
        return elapsed
    except Exception as e:
        print(f"官方预置音色生成失败: {e}")
        return None

def test_clone(reference_path: Path):
    print("--- 开始测试声音克隆音色 (mimo-v2.5-tts-voiceclone) ---")
    
    # 编码参考音频
    ref_uri = audio_data_uri(reference_path)
    
    payload = {
        "model": "mimo-v2.5-tts-voiceclone",
        "messages": [
            {"role": "user", "content": "自然、清晰、温暖的讲故事语气，语速稍慢，适合日常故事分享。"},
            {"role": "assistant", "content": "苏轼和王安石是宋代非常有名的文学家，他们曾经是很好的朋友，也写过很多美妙的诗歌。"},
        ],
        "audio": {
            "format": "wav",
            "voice": ref_uri,
        },
        "stream": False,
    }
    
    start_time = time.time()
    try:
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
        end_time = time.time()
        elapsed = end_time - start_time
        choices = data.get("choices") or [{}]
        has_audio = bool(choices[0].get("message", {}).get("audio", {}).get("data"))
        print(f"声音克隆音色生成成功！耗时: {elapsed:.2f} 秒 (是否成功返回音频: {has_audio})")
        return elapsed
    except Exception as e:
        print(f"声音克隆音色生成失败: {e}")
        return None

def main():
    ref_path = Path(__file__).resolve().parents[2] / "资源" / "官方预置声音" / "白桦_成年男.wav"
    if not ref_path.exists():
        print(f"警告: 找不到克隆参考音频文件：{ref_path}，无法进行克隆测试。")
        return
        
    t_preset = test_preset()
    print()
    t_clone = test_clone(ref_path)
    print()
    
    if t_preset and t_clone:
        diff = t_clone - t_preset
        pct = (t_clone / t_preset - 1) * 100
        print("=== 测试结论 ===")
        print(f"官方预置音色耗时: {t_preset:.2f} 秒")
        print(f"声音克隆音色耗时: {t_clone:.2f} 秒")
        print(f"声音克隆相比官方预置音色多耗时: {diff:.2f} 秒 (慢了约 {pct:.1f}%)")

if __name__ == "__main__":
    main()
