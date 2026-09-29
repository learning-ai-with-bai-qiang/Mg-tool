"""
compose_video.py —— 音画合成最终视频脚本   
用法：直接运行，自动扫描 workspace/shots/ 下所有分镜，逐个合成
功能：把每个分镜的 frames/ + audio.wav 合成为 final.mp4
AUDIO_DELAY = 0.25 (最合适)  # 音频延迟秒数（画面比声音提前）
"""

import os
import subprocess
from pathlib import Path

# ========== 路径配置 ==========
from paths import resource_path, workspace_path, ffmpeg_path, CREATE_NO_WINDOW # ← ① 新增

SHOTS_ROOT = workspace_path("shots")              # ← ② 改动

# ========== ffmpeg 路径 ==========
FFMPEG_BIN_DIR = ffmpeg_path()    # ← ② 改动
if FFMPEG_BIN_DIR.exists():
    os.environ["PATH"] = str(FFMPEG_BIN_DIR) + os.pathsep + os.environ["PATH"]
    FFMPEG = str(FFMPEG_BIN_DIR / "ffmpeg.exe")
else:
    FFMPEG = "ffmpeg"

# ========== 合成配置 ==========
#FPS = 30             # 帧率，和渲染时一致
AUDIO_DELAY = 0.25   # 音频延迟秒数（画面比声音提前）

# ↓↓↓ 以下到 main 结束，一个字没动 ↓↓↓

# ========== 合成单个分镜 ==========

def compose_shot(shot_dir):
    shot_id = shot_dir.name
    silent_video = shot_dir / "silent.mp4"
    audio_file = shot_dir / "audio.wav"
    output_file = shot_dir / "final.mp4"

    print(f"\n🎬 处理：{shot_id}")

    if output_file.exists():
        print(f"   ⏭️ final.mp4 已存在，跳过")
        return

    if not silent_video.exists():
        print(f"   ⚠️ 找不到 silent.mp4，跳过")
        return
    if not audio_file.exists():
        print(f"   ⚠️ 找不到 audio.wav，跳过")
        return

    print(f"   🎬 无声视频：{silent_video.name}")
    print(f"   🎵 音频：{audio_file.name}")

    cmd = [
        FFMPEG,
        "-i", str(silent_video),
        "-itsoffset", str(AUDIO_DELAY),
        "-i", str(audio_file),
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        "-y",
        str(output_file)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",creationflags=CREATE_NO_WINDOW)
        if result.returncode != 0:
            print(f"   ❌ 合成失败：")
            print(result.stderr[-500:] if result.stderr else "未知错误")
            return
    except Exception as e:
        print(f"   ❌ 执行出错：{e}")
        return

    if output_file.exists():
        size_mb = output_file.stat().st_size / (1024 * 1024)
        print(f"   ✅ 合成完成：{output_file.name}（{size_mb:.2f} MB）")
    else:
        print(f"   ❌ 输出文件未生成")


# ========== 主流程 ==========

def main():
    if not SHOTS_ROOT.exists():
        print(f"❌ 找不到目录：{SHOTS_ROOT}")
        return

    shot_dirs = sorted([d for d in SHOTS_ROOT.iterdir() if d.is_dir() and d.name.startswith("shot_")])

    if not shot_dirs:
        print(f"⚠️ {SHOTS_ROOT} 下没有 shot_* 文件夹")
        return

    print(f"📂 找到 {len(shot_dirs)} 个分镜")

    for shot_dir in shot_dirs:
        compose_shot(shot_dir)

    print(f"\n✅ 全部分镜处理完成")


if __name__ == "__main__":
    main()