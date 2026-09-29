# audio_to_timestamp.py
# 从 script.txt 读取原文，用 stable_whisper 生成逐字时间戳

import stable_whisper
import json
import re
import os
import subprocess
import numpy as np          # 没有就加
from pathlib import Path
from paths import CREATE_NO_WINDOW

# ==================== patch whisper 的 load_audio，加 CREATE_NO_WINDOW ====================
# 原因：stable_whisper.audio.load_audio 内部调 subprocess.run 调 ffmpeg 时，
# 没带 creationflags，打包后会弹黑框。这里替换掉这个函数，加上参数。
import numpy as _np
import subprocess as _sp
from stable_whisper.audio import SAMPLE_RATE as _SR, load_source as _load_source

# ================= 路径配置 =================
from paths import resource_path, workspace_path, ffmpeg_path   # ← ① 新增

SHOTS_ROOT = workspace_path("shots")              # ← ② 改动
MODEL_SIZE = "base"  # 可改为 small、medium 提高精度

# ================= ffmpeg 路径 =================
FFMPEG_BIN_DIR = ffmpeg_path()      # ← ② 改动
if FFMPEG_BIN_DIR.exists():
    os.environ["PATH"] = str(FFMPEG_BIN_DIR) + os.pathsep + os.environ["PATH"]
    FFMPEG = str(FFMPEG_BIN_DIR / "ffmpeg.exe")
    FFPROBE = str(FFMPEG_BIN_DIR / "ffprobe.exe")
else:
    FFMPEG = "ffmpeg"
    FFPROBE = "ffprobe"

# ================= 主流程 =================
# ↓↓↓ 以下到 batch_extract 结束，一个字没动 ↓↓↓

def extract_voice_texts_from_config(config_path):
    """从 config.js 中提取所有 voice_text 字段"""
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = r'voice_text\s*:\s*["\']([^"\']+)["\']'
    return re.findall(pattern, content)


def batch_extract():
    """扫描所有分镜，逐个生成时间戳"""
    if not SHOTS_ROOT.exists():
        print(f"❌ 找不到目录：{SHOTS_ROOT}")
        return

    shot_dirs = sorted([d for d in SHOTS_ROOT.iterdir() if d.is_dir() and d.name.startswith("shot_")])

    if not shot_dirs:
        print(f"⚠️ {SHOTS_ROOT} 下没有 shot_* 文件夹")
        return

    print(f"📂 找到 {len(shot_dirs)} 个分镜")
    print("⏳ 加载模型（只需加载一次）...")
    model = stable_whisper.load_model(MODEL_SIZE)

    for shot_dir in shot_dirs:
        shot_id = shot_dir.name

        if (shot_dir / "timestamps.json").exists():
            print(f"\n⏭️ {shot_id}：timestamps.json 已存在，跳过")
            continue

        script_file = shot_dir / "script.txt"
        audio_file = shot_dir / "audio.wav"
        out_json_path = shot_dir / "timestamps.json"

        print(f"\n🎬 处理：{shot_id}")

        if not script_file.exists():
            print(f"   ⚠️ 找不到 script.txt，跳过")
            continue
        if not audio_file.exists():
            print(f"   ⚠️ 找不到 audio.wav，跳过")
            continue

        with open(script_file, "r", encoding="utf-8") as f:
            full_text = f.read().strip()

        if not full_text:
            print(f"   ❌ script.txt 是空的")
            continue

        print(f"   📝 台词长度：{len(full_text)} 字")

        try:
            # 自己读音频（带 CREATE_NO_WINDOW），绕开 whisper 内部的 ffmpeg 调用
            import numpy as _np
            _cmd = [
                FFMPEG, "-nostdin", "-threads", "0",
                "-i", str(audio_file),
                "-f", "s16le",
                "-ac", "1",
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-"
            ]
            _out = subprocess.run(
                _cmd, capture_output=True, check=True,
                creationflags=CREATE_NO_WINDOW
            ).stdout
            _audio_array = _np.frombuffer(_out, _np.int16).flatten().astype(_np.float32) / 32768.0

            result = model.align(_audio_array, full_text, language="zh")
            word_list = []
            for seg in result.segments:
                if not hasattr(seg, "words"):
                    continue
                for word_info in seg.words:
                    word_list.append({
                        "text": word_info.word.strip(),
                        "start": round(word_info.start, 2),
                        "end": round(word_info.end, 2)
                    })
            with open(out_json_path, "w", encoding="utf-8") as f:
                json.dump(word_list, f, ensure_ascii=False, indent=2)
            print(f"   ✅ 时间戳已保存：{out_json_path.name}（{len(word_list)} 个词）")
        except Exception as e:
            print(f"   ❌ 对齐失败：{e}")


# ================= 入口 =================

def main():                    # ← ③ 新增
    batch_extract()


if __name__ == "__main__":     # ← ③ 新增
    main()