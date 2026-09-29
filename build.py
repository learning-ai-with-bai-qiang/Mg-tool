# build.py —— 一键打包（打包 + 整理 + 杀进程）
# 用法：python build.py
import subprocess
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist" / "mg_tool"
INTERNAL = DIST / "_internal"


def kill_running_exe():
    """打包前，先杀掉正在运行的 mg_tool.exe"""
    print("[build] 检查是否有正在运行的 mg_tool.exe...")
    result = subprocess.run(
        ["taskkill", "/F", "/IM", "mg_tool.exe"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("[build] 已关闭正在运行的 mg_tool.exe")
        time.sleep(1)
    else:
        print("[build] 没有正在运行的 mg_tool.exe")


def main():
    # 0. 先杀进程
    kill_running_exe()

    # 1. 调 PyInstaller 打包
    print("=" * 60)
    print("[build] 开始打包...")
    print("=" * 60)
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "mg_tool.spec", "--clean", "--noconfirm"],
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        print("\n[build] ❌ 打包失败")
        sys.exit(1)

    # 2. 把 ms-playwright 从 _internal 挪到 EXE 同级
    print("\n" + "=" * 60)
    print("[build] 整理打包结果...")
    print("=" * 60)

    src = INTERNAL / "ms-playwright"
    dst = DIST / "ms-playwright"

    if src.exists():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.move(str(src), str(dst))
        print("[build] ✅ ms-playwright 已挪到 EXE 同级")
    else:
        print(f"[build] ⚠️ 没找到 {src}，跳过")

    # 把 LICENSE 和 THIRD-PARTY-NOTICES.md 从 _internal 挪到 EXE 同级
    for fname in ["LICENSE", "THIRD-PARTY-NOTICES.md"]:
        src = INTERNAL / fname
        dst = DIST / fname
        if src.exists():
            if dst.exists():
                dst.unlink()
            shutil.move(str(src), str(dst))
            print(f"[build] ✅ {fname} 已挪到 EXE 同级")
        else:
            print(f"[build] ⚠️ 没找到 {src}，跳过")
   
    # 3. 检查 ffmpeg（打包进 _internal/assets/ffmpeg/bin）
    ffmpeg_dir = INTERNAL / "assets" / "ffmpeg" / "bin"
    if (ffmpeg_dir / "ffmpeg.exe").exists() and (ffmpeg_dir / "ffprobe.exe").exists():
        print("[build] ✅ ffmpeg 已打包进 _internal/assets/ffmpeg/bin")
    else:
        print(f"[build] ⚠️ 没找到 ffmpeg：{ffmpeg_dir}")
    print("\n" + "=" * 60)
    print(f"[build] 🎉 完成！产物在：{DIST}")
    print("=" * 60)

if __name__ == "__main__":
    main()