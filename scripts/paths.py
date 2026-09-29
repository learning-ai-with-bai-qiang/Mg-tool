# paths.py —— 统一路径管理，本地和打包后都能用
# 放在 scripts/ 目录里，跟 7 个脚本同级

import sys
from pathlib import Path

# Windows 专用：subprocess 子进程不弹黑框
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

def _dev_root():
    """开发模式下的 mg_tool 根目录（paths.py 在 scripts/ 里，往上两级）"""
    return Path(__file__).parent.parent


def resource_path(rel=""):
    """
    只读资源：engine.html / ffmpeg / prompt.md
    本地：mg_tool/ 根目录
    打包后：PyInstaller 解压目录（sys._MEIPASS）
    """
    if getattr(sys, "_MEIPASS", None):
        base = Path(sys._MEIPASS)
    else:
        base = _dev_root()
    return base / rel

def ffmpeg_path():
    """ffmpeg 目录：开发时是项目根/assets/ffmpeg/bin，打包后是 _MEIPASS/assets/ffmpeg/bin"""
    if getattr(sys, "_MEIPASS", None):
        base = Path(sys._MEIPASS)
    else:
        base = _dev_root()
    return base / "assets" / "ffmpeg" / "bin"

# ==================== subprocess 全局去黑框 ====================
# 只 patch run，不动 Popen（patch Popen 会破坏 asyncio 的继承）
import subprocess as _sp

_original_run = _sp.run

def _run_no_window(*args, **kwargs):
    kwargs.setdefault("creationflags", CREATE_NO_WINDOW)
    return _original_run(*args, **kwargs)

_sp.run = _run_no_window

def workspace_path(rel=""):
    """
    可写数据：workspace/shots（用户分镜数据）
    本地：mg_tool/workspace
    打包后：EXE 同级的 workspace（永远不放进 _MEIPASS）
    """
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = _dev_root()
    return base / "workspace" / rel