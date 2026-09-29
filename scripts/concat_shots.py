"""
concat_shots.py —— 把所有分镜的 final.mp4 按顺序拼接成完整视频
用法：直接运行
"""
import os
import subprocess
import sys
from pathlib import Path

# ========== 路径配置 ==========
from paths import resource_path, workspace_path, ffmpeg_path, CREATE_NO_WINDOW  # ← ① 新增

WORKSPACE_ROOT = workspace_path("")                # ← ② 改动（传空串取 workspace 根）
SHOTS_ROOT = workspace_path("shots")               # ← ② 改动
OUTPUT_FILE = WORKSPACE_ROOT / "full_video.mp4"
LIST_FILE = WORKSPACE_ROOT / "concat_list.txt"

# ========== ffmpeg 路径 ==========
FFMPEG_BIN_DIR = ffmpeg_path()       # ← ② 改动
if FFMPEG_BIN_DIR.exists():
    os.environ["PATH"] = str(FFMPEG_BIN_DIR) + os.pathsep + os.environ["PATH"]
    FFMPEG = str(FFMPEG_BIN_DIR / "ffmpeg.exe")
else:
    FFMPEG = "ffmpeg"

# ↓↓↓ 以下到 main 结束，除 sys.exit 改 return，其他一字没动 ↓↓↓

def main():
    if not SHOTS_ROOT.exists():
        print(f"❌ 找不到目录：{SHOTS_ROOT}")
        return                                     # ← ③ sys.exit(1) → return

    # 找所有 shot_XX/final.mp4，按编号排序
    shot_files = sorted(SHOTS_ROOT.glob("shot_*/final.mp4"))

    if not shot_files:
        print("❌ 没有找到任何分镜视频")
        print(f"   请确认 {SHOTS_ROOT} 下有 shot_01/final.mp4 这样的文件")
        return                                     # ← ③ sys.exit(1) → return

    print(f"📦 找到 {len(shot_files)} 个分镜：")
    for f in shot_files:
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"   - {f.parent.name} / final.mp4  ({size_mb:.2f} MB)")

    # 生成 concat 列表
    with open(LIST_FILE, "w", encoding="utf-8") as f:
        for shot in shot_files:
            f.write(f"file '{shot.as_posix()}'\n")

    print(f"\n📝 拼接列表已生成：{LIST_FILE.name}")
    print(f"🎬 开始拼接...")

    # 先尝试直接 copy（快，不重新编码）
    cmd = [
        FFMPEG,
        "-f", "concat",
        "-safe", "0",
        "-i", str(LIST_FILE),
        "-c", "copy",
        "-y",
        str(OUTPUT_FILE)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",creationflags=CREATE_NO_WINDOW)

    if result.returncode != 0:
        print("⚠️ 直接 copy 失败，尝试重新编码...")
        # 回退方案：重新编码
        cmd = [
            FFMPEG,
            "-f", "concat",
            "-safe", "0",
            "-i", str(LIST_FILE),
            "-c:v", "libopenh264",
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            "-y",
            str(OUTPUT_FILE)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",creationflags=CREATE_NO_WINDOW)
        if result.returncode != 0:
            print("❌ 拼接失败：")
            print(result.stderr[-1000:])
            return                                 # ← ③ sys.exit(1) → return

    if OUTPUT_FILE.exists():
        size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
        print(f"\n✅ 拼接完成！")
        print(f"📁 输出文件：{OUTPUT_FILE}")
        print(f"📊 文件大小：{size_mb:.2f} MB")
    else:
        print("❌ 输出文件未生成")
        return                                     # ← ③ sys.exit(1) → return


if __name__ == "__main__":
    main()