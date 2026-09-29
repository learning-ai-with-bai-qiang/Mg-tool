"""
render_frames.py —— MG 动画逐帧渲染脚本 直接生成无声视频
用法：直接运行，自动扫描 workspace/shots/ 下所有分镜
管道方案：截图不落地，直接喂给 ffmpeg，输出 silent.mp4
"""

import os
import sys
import time
import math
import json
import subprocess
import threading
import queue
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

def find_chromium_exe():
    """自动扫描 ms-playwright 目录，找到最新版的 chrome.exe"""
    base = Path(sys.executable).parent / "ms-playwright"
    if not base.exists():
        return None

    candidates = []
    for d in base.iterdir():
        if d.is_dir() and d.name.startswith("chromium-") and not d.name.startswith("chromium_headless"):
            exe = d / "chrome-win64" / "chrome.exe"
            if exe.exists():
                m = re.search(r'chromium-(\d+)', d.name)
                ver = int(m.group(1)) if m else 0
                candidates.append((ver, exe))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]

# ================= 路径配置 =================
from paths import resource_path,workspace_path, ffmpeg_path, CREATE_NO_WINDOW

SHOTS_ROOT = workspace_path("shots")

# ================= ffmpeg 路径 =================
FFMPEG_BIN_DIR = ffmpeg_path()
if FFMPEG_BIN_DIR.exists():
    os.environ["PATH"] = str(FFMPEG_BIN_DIR) + os.pathsep + os.environ["PATH"]
    FFMPEG = str(FFMPEG_BIN_DIR / "ffmpeg.exe")
    FFPROBE = str(FFMPEG_BIN_DIR / "ffprobe.exe")
else:
    FFMPEG = "ffmpeg"
    FFPROBE = "ffprobe"

# ================= 渲染配置 =================
FPS = 30
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080

# ================= 进度回调 =================
_progress_callback = None

def set_progress_callback(cb):
    """外部注册回调，渲染时每帧喊一声"""
    global _progress_callback
    _progress_callback = cb


def get_audio_duration(audio_path):
    """用 ffprobe 读取音频真实时长（秒）"""
    cmd = [
        FFPROBE, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json", str(audio_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe 读取音频失败：{result.stderr}")
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def render_shot(shot_dir, frame_callback=None):
    shot_id = shot_dir.name
    html_file = shot_dir / "engine.html"
    audio_file = shot_dir / "audio.wav"
    size_file = shot_dir / "mg_config_size.json"
    config_file = shot_dir / "mg_config.js"
    silent_video = shot_dir / "silent.mp4"

    print(f"\n🎬 处理：{shot_id}")

    if silent_video.exists():
        print(f"   ⏭️ silent.mp4 已存在，跳过")
        return

    if not config_file.exists():
        print(f"   ⚠️ 找不到 mg_config.js，跳过")
        return
    content = config_file.read_text(encoding="utf-8")
    values = re.findall(r'start_time\s*:\s*([\d.]+)', content)
    if not values or any(float(v) == 0 for v in values):
        print(f"   ⚠️ start_time 未填好，跳过渲染")
        return

    if not html_file.exists():
        print(f"   ⚠️ 找不到 engine.html，跳过")
        return
    if not audio_file.exists():
        print(f"   ⚠️ 找不到 audio.wav，跳过")
        return

    total_duration = get_audio_duration(audio_file)
    total_frames = math.ceil(total_duration * FPS)
    print(f"   🎵 音频 {total_duration:.2f}s，共 {total_frames} 帧")

    ffmpeg_cmd = [
        FFMPEG,
        "-f", "image2pipe",
        "-c:v", "mjpeg",
        "-framerate", str(FPS),
        "-i", "-",
        "-c:v", "libopenh264",
        "-pix_fmt", "yuv420p",
        "-y",
        str(silent_video)
    ]

    proc = subprocess.Popen(
        ffmpeg_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW
    )

    frame_queue = queue.Queue(maxsize=5)

    def writer():
        while True:
            data = frame_queue.get()
            if data is None:
                break
            try:
                proc.stdin.write(data)
                proc.stdin.flush()
            except Exception as e:
                print(f"   ❌ 写管道失败：{e}")
                break
        try:
            proc.stdin.close()
        except Exception:
            pass

    writer_thread = threading.Thread(target=writer)
    writer_thread.start()

    with sync_playwright() as p:
        if getattr(sys, "frozen", False):
            _chrome = find_chromium_exe()
            if _chrome:
                browser = p.chromium.launch(headless=True, executable_path=str(_chrome))
            else:
                raise RuntimeError("找不到 chromium，请检查 ms-playwright 目录")
        else:
            browser = p.chromium.launch(headless=True)

        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            device_scale_factor=1.5
        )
        page = context.new_page()

        file_url = f"file:///{html_file.resolve().as_posix()}?render=1&t={int(time.time())}"
        page.goto(file_url)
        page.wait_for_timeout(1000)

        if size_file.exists():
            with open(size_file, "r", encoding="utf-8") as f:
                adjustments = json.load(f)
            page.evaluate("(adj) => window.applySizeAdjustments(adj)", adjustments)
            print(f"   📐 已应用 {len(adjustments)} 个尺寸调整")

        print(f"   🎬 开始渲染...")
        start_time = time.time()

        for frame_index in range(total_frames):
            t = frame_index / FPS
            page.evaluate(f"window.seek({t})")
            page.wait_for_timeout(10)

            frame_bytes = page.locator("#stage").screenshot(
                type="jpeg",
                quality=95
            )
            frame_queue.put(frame_bytes)

            if frame_callback:
                frame_callback(frame_index + 1, total_frames)

            if frame_index % 30 == 0:
                elapsed = time.time() - start_time
                progress = (frame_index + 1) / total_frames * 100
                print(f"   ⏱️ 进度 {progress:.1f}% | 已用 {elapsed:.1f}s")
        browser.close()

    frame_queue.put(None)
    writer_thread.join()
    proc.wait()

    elapsed = time.time() - start_time

    if silent_video.exists():
        size_mb = silent_video.stat().st_size / (1024 * 1024)
        print(f"   ✅ {shot_id} 完成：{total_frames} 帧，{size_mb:.2f} MB，耗时 {elapsed:.1f}s")
    else:
        print(f"   ❌ {shot_id} silent.mp4 未生成")


def main():
    if not SHOTS_ROOT.exists():
        print(f"❌ 找不到目录：{SHOTS_ROOT}")
        return

    shot_dirs = sorted([d for d in SHOTS_ROOT.iterdir() if d.is_dir() and d.name.startswith("shot_")])

    if not shot_dirs:
        print(f"⚠️ {SHOTS_ROOT} 下没有 shot_* 文件夹")
        return

    # 只算需要渲染的（没 silent.mp4 的）
    need_render = [d for d in shot_dirs if not (d / "silent.mp4").exists()]

    print(f"📂 找到 {len(shot_dirs)} 个分镜，需要渲染 {len(need_render)} 个")

    if not need_render:
        if _progress_callback:
            _progress_callback(1.0)
        return

    total_shots = len(need_render)

    for idx, shot_dir in enumerate(need_render):
        base = idx / total_shots
        rng = 1 / total_shots

        def make_cb(b, r):
            def cb(current, total):
                if _progress_callback:
                    _progress_callback(b + (current / total) * r)
            return cb

        render_shot(shot_dir, frame_callback=make_cb(base, rng))

    print(f"\n✅ 全部渲染完成")


if __name__ == "__main__":
    main()