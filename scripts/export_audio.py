# export_audio.py - 从视频中提取音频并剪掉空白
# 用法：本地 python export_audio.py，打包后由 app.py 直接调 main()

import subprocess
import json
import re
import os
from pathlib import Path

# ================= 路径配置 =================
from paths import resource_path,CREATE_NO_WINDOW, workspace_path, ffmpeg_path   # ← ① 新增

SHOTS_ROOT = workspace_path("shots")              # ← ② 改动

# ================= ffmpeg 路径 =================
FFMPEG_BIN_DIR = ffmpeg_path()      # ← ② 改动
if FFMPEG_BIN_DIR.exists():
    os.environ["PATH"] = str(FFMPEG_BIN_DIR) + os.pathsep + os.environ["PATH"]
    FFMPEG = str(FFMPEG_BIN_DIR / "ffmpeg.exe")
    FFPROBE = str(FFMPEG_BIN_DIR / "ffprobe.exe")
else:
    FFMPEG = "ffmpeg"
    FFPROBE = "ffprobe"

# ================= 通用工具函数 =================
# ↓↓↓ 以下到 extract_all_audio 结束，一个字没动 ↓↓↓

def get_audio_duration(audio_path: Path) -> float:
    """获取音频时长（秒）"""
    cmd = [
        FFPROBE, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json", str(audio_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def detect_speech_region(audio_path: Path, silence_threshold: str = "-30dB", min_silence: float = 0.5):
    """用 silencedetect 检测静音段，返回有效语音的起始和结束时间"""
    cmd = [
        FFMPEG, "-i", str(audio_path),
        "-af", f"silencedetect=noise={silence_threshold}:d={min_silence}",
        "-f", "null", "-"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
    stderr = result.stderr

    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", stderr)]

    if not starts:
        return 0.0, get_audio_duration(audio_path)

    speech_start = ends[0] if ends else 0.0
    speech_end = starts[-1] if starts else get_audio_duration(audio_path)
    return speech_start, speech_end


def extract_and_trim_audio(video_path: Path, output_audio_path: Path,
                           silence_threshold: str = "-30dB",
                           min_silence: float = 0.5,
                           padding: float = 0.3) -> bool:
    """从视频提取音频，裁剪静音段，输出干净的 WAV"""
    temp_audio = video_path.with_suffix(".tmp.wav")
    extract_cmd = [
        FFMPEG, "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le",
        "-y", str(temp_audio)
    ]
    subprocess.run(extract_cmd, capture_output=True, creationflags=CREATE_NO_WINDOW)

    start, end = detect_speech_region(temp_audio, silence_threshold, min_silence)

    start = max(0, start - padding)
    total_duration = get_audio_duration(temp_audio)
    end = min(total_duration, end + padding)

    if end <= start:
        print(f"⚠️ {video_path.name} 未检测到有效语音，跳过")
        temp_audio.unlink(missing_ok=True)
        return False

    trim_cmd = [
        FFMPEG, "-i", str(temp_audio),
        "-ss", str(start),
        "-to", str(end),
        "-c", "copy",
        "-y", str(output_audio_path)
    ]
    subprocess.run(trim_cmd, capture_output=True, creationflags=CREATE_NO_WINDOW)

    temp_audio.unlink(missing_ok=True)
    return True


# ================= 主流程 =================

def extract_all_audio():
    """扫描 workspace/shots/ 下所有 shot_* 文件夹，逐个提取音频"""
    if not SHOTS_ROOT.exists():
        print(f"❌ 找不到目录：{SHOTS_ROOT}")
        return

    shot_dirs = sorted([d for d in SHOTS_ROOT.iterdir() if d.is_dir() and d.name.startswith("shot_")])

    if not shot_dirs:
        print(f"⚠️ {SHOTS_ROOT} 下没有 shot_* 文件夹")
        return

    print(f"📂 找到 {len(shot_dirs)} 个分镜，开始处理")
    success_count = 0

    for shot_dir in shot_dirs:
        shot_id = shot_dir.name
        output_audio = shot_dir / "audio.wav"

        if output_audio.exists():
            print(f"\n⏭️ {shot_id}：audio.wav 已存在，跳过")
            continue

        vid_files = list(shot_dir.glob("VID_*.mp4"))
        if not vid_files:
            print(f"\n⚠️ {shot_id} 里没有 VID_*.mp4，跳过")
            continue

        video_path = vid_files[0]

        print(f"\n🎬 处理：{shot_id} ← {video_path.name}")
        success = extract_and_trim_audio(video_path, output_audio)

        if success:
            duration = get_audio_duration(output_audio)
            print(f"   ✅ 音频已保存，时长 {duration:.2f} 秒")
            success_count += 1
        else:
            print(f"   ❌ 处理失败")

    print(f"\n✅ 完成：成功 {success_count}/{len(shot_dirs)} 个分镜")


# ================= 入口 =================

def main():                    # ← ③ 新增：给外部（run_pipeline / app.py）调用的入口
    extract_all_audio()


if __name__ == "__main__":     # ← ③ 新增：本地单独跑时也走这里
    main()