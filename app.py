# app.py —— MG 动画工具入口
import sys
import os
import subprocess
from pathlib import Path

# ==================== 【最优先】确保 VC++ 运行库 ====================
def _ensure_vcredist_early():
    """必须在 import torch 之前执行，否则 torch 的 dll 加载失败会直接崩溃"""
    if not getattr(sys, "frozen", False):
        return
    try:
        sys32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
        if (sys32 / "vcruntime140.dll").exists():
            return
        vc_exe = Path(sys._MEIPASS) / "assets" / "VC_redist.x64.exe"
        if vc_exe.exists():
            print("[VC++] 正在静默安装...")
            subprocess.run([str(vc_exe), "/quiet", "/norestart"], capture_output=True)
            print("[VC++] 安装完成")
    except Exception as e:
        print(f"[VC++] 出错：{e}")

_ensure_vcredist_early()
# ====================================================================

# ========== 现在才 import 其他东西 ==========
import webview
import shutil
import json
import threading

sys.path.insert(0, str(Path(__file__).parent / "scripts"))
import export_audio
import audio_to_timestamp
import match_shots
import render_frames
import compose_video
import concat_shots

# 打包后，Windows 下 stdout 默认是 GBK，遇到 emoji 会报错，强制改成 UTF-8
if sys.platform == "win32":
    try:
        if sys.stdout is not None:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr is not None:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def _app_root():
    """数据目录：打包后是 EXE 同级，开发时是项目根目录"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent

def _res_root():
    """资源目录：打包后是 PyInstaller 解压目录，开发时是项目根目录"""
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS)
    return Path(__file__).parent

BASE_DIR = _app_root()              # 数据：workspace、archives、ffmpeg
RES_DIR = _res_root()               # 资源：web、assets

INDEX_HTML = RES_DIR / "web" / "index.html"
WORKSPACE_ROOT = BASE_DIR / "workspace"
SHOTS_ROOT = WORKSPACE_ROOT / "shots"
ASSETS_DIR = RES_DIR / "assets"

def get_clipboard_text():
    import pyperclip
    try:
        return pyperclip.paste()
    except Exception:
        return ""

def clean_config_text(text):
    # 统一换行符：把 Windows 的 CRLF 转成 LF，避免 \ 后面跟 CR 报错
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    """清洗剪贴板内容：剥掉代码块标记，只留 window.SCENES = [...] 这一段"""
    text = text.strip()

    start = text.find("window.SCENES")
    if start == -1:
        return text

    text = text[start:]

    end = text.rfind("];")
    if end != -1:
        text = text[:end + 2]

    return text.strip()

# ================= 分镜文件夹管理 =================

def create_shot(shot_id):
    """创建一个分镜文件夹：空 script.txt + 复制 engine.html"""
    shot_dir = SHOTS_ROOT / shot_id
    shot_dir.mkdir(exist_ok=True)

    script_file = shot_dir / "script.txt"
    if not script_file.exists():
        script_file.write_text("", encoding="utf-8")

    engine_src = ASSETS_DIR / "engine.html"
    engine_dst = shot_dir / "engine.html"
    if engine_src.exists() and not engine_dst.exists():
        shutil.copy(engine_src, engine_dst)


def ensure_workspace():
    """工具启动时：保证 workspace/shots/ 存在，至少有一个 shot_01"""
    SHOTS_ROOT.mkdir(parents=True, exist_ok=True)

    shots = [d for d in SHOTS_ROOT.iterdir() if d.is_dir() and d.name.startswith("shot_")]
    if not shots:
        create_shot("shot_01")
    refresh_all_templates()

def refresh_all_templates():
    """把所有分镜的 engine.html 刷成最新模板"""
    src = ASSETS_DIR / "engine.html"
    if not src.exists() or not SHOTS_ROOT.exists():
        return
    for shot_dir in SHOTS_ROOT.iterdir():
        if shot_dir.is_dir() and shot_dir.name.startswith("shot_"):
            shutil.copy(src, shot_dir / "engine.html")     

def get_shot_status(shot_dir):
    """判断分镜状态：done / doing / todo"""
    # 已完成：有 final.mp4
    if (shot_dir / "final.mp4").exists():
        return "done"

    # 进行中：文件类
    doing_files = [
        "mg_config.js",
        "mg_config_size.json",
        "audio.wav",
        "timestamps.json",
        "silent.mp4",
    ]
    for name in doing_files:
        if (shot_dir / name).exists():
            return "doing"

    # 进行中：导入了视频（VID_ 开头）
    if list(shot_dir.glob("VID_*.mp4")):
        return "doing"

    # 进行中：script.txt 有内容
    script = shot_dir / "script.txt"
    if script.exists() and script.read_text(encoding="utf-8").strip():
        return "doing"

    # 剩下就是未完成（只有 engine.html + 空 script.txt）
    return "todo"

# ================= 暴露给前端的 API =================

class Api:

    def _push_js(self, js_code):
        """给前端推一段 JS"""
        try:
            webview.windows[0].evaluate_js(js_code)
        except Exception:
            pass

    def get_shot_list(self):
        """扫描 workspace/shots/，返回分镜列表"""
        if not SHOTS_ROOT.exists():
            return []

        shot_dirs = sorted(
            [d for d in SHOTS_ROOT.iterdir()
             if d.is_dir() and d.name.startswith("shot_")],
            key=lambda d: d.name
        )

        result = []
        for shot_dir in shot_dirs:
            result.append({
                "id": shot_dir.name,
                "status": get_shot_status(shot_dir),
            })
        return result

    def get_script(self, shot_id):
        """读分镜的 script.txt"""
        script_file = SHOTS_ROOT / shot_id / "script.txt"
        if not script_file.exists():
            return ""
        return script_file.read_text(encoding="utf-8")

    def save_script(self, shot_id, text):
        """把文案写进 script.txt，并返回新状态"""
        shot_dir = SHOTS_ROOT / shot_id
        if not shot_dir.exists():
            return None
        (shot_dir / "script.txt").write_text(text, encoding="utf-8")
        return get_shot_status(shot_dir)

    def new_shot(self):
        """新建分镜：找缺口，建文件夹，返回新 id"""
        existing = set()
        for d in SHOTS_ROOT.iterdir():
            if d.is_dir() and d.name.startswith("shot_"):
                try:
                    existing.add(int(d.name[5:]))
                except ValueError:
                    pass

        n = 1
        while n in existing:
            n += 1

        shot_id = f"shot_{n:02d}"
        create_shot(shot_id)
        return shot_id

    def delete_shots(self, shot_ids):
        """删除指定的分镜文件夹"""
        import shutil
        for sid in shot_ids:
            shot_dir = SHOTS_ROOT / sid
            if shot_dir.exists():
                shutil.rmtree(shot_dir)
        return True

    def build_prompt(self, shot_id):
        """拼接提示词 + 文案，返回拼接结果。文案为空返回 None"""
        script_file = SHOTS_ROOT / shot_id / "script.txt"
        prompt_file = ASSETS_DIR / "generate_prompt.md"

        if not script_file.exists() or not prompt_file.exists():
            return None

        script_text = script_file.read_text(encoding="utf-8").strip()
        if not script_text:
            return None

        prompt_text = prompt_file.read_text(encoding="utf-8").strip()

        separator = "\n\n==========\n原始文案如下\n\n"

        return prompt_text + separator + script_text

    def read_config_from_clipboard(self):
        """读剪贴板，清洗，校验，返回预览内容 + 第一条 voice_text（不写文件）"""
        raw = get_clipboard_text()
        if not raw or not raw.strip():
            return {"ok": False, "msg": "clipboard_empty"}

        cleaned = clean_config_text(raw)

        if "window.SCENES" not in cleaned:
            return {"ok": False, "msg": "not_config"}

        # 抓第一条 voice_text
        import re
        match = re.search(r'voice_text\s*:\s*["\']([^"\']+)["\']', cleaned)
        first_voice_text = match.group(1) if match else ""

        return {
            "ok": True,
            "content": cleaned,
            "first_voice_text": first_voice_text,
        }

    def save_config(self, shot_id, content):
        """把配置内容写入分镜"""
        shot_dir = SHOTS_ROOT / shot_id
        if not shot_dir.exists():
            return {"ok": False, "msg": "分镜不存在"}

        (shot_dir / "mg_config.js").write_text(content, encoding="utf-8")

        status = get_shot_status(shot_dir)
        return {"ok": True, "status": status}

    def import_video(self, shot_id, overwrite=False):
        """导入视频：弹文件选择框 → 复制进分镜 → 改前缀为 VID_"""
        shot_dir = SHOTS_ROOT / shot_id
        if not shot_dir.exists():
            return {"ok": False, "msg": "分镜不存在"}

        existing = list(shot_dir.glob("VID_*.mp4"))
        if existing and not overwrite:
            return {"ok": False, "msg": "already_has_video"}
    
        # 弹文件选择框
        result = webview.windows[0].create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=("MP4 视频 (*.mp4)",)
        )
        if not result:
            return {"ok": False, "msg": "canceled"}

        src = Path(result[0])

        # 构造新名字：把前缀换成 VID_
        name = src.name
        if "_" in name:
            new_name = "VID_" + name.split("_", 1)[1]
        else:
            new_name = "VID_" + name

        # 删旧的
        for f in existing:
            f.unlink()

        # 复制新的
        shutil.copy(src, shot_dir / new_name)

        status = get_shot_status(shot_dir)
        return {"ok": True, "status": status, "filename": new_name}

    def preview_shot(self, shot_id):
        """弹预览窗口，加载分镜的 engine.html"""
        shot_dir = SHOTS_ROOT / shot_id
        html_file = shot_dir / "engine.html"
        if not html_file.exists():
            return {"ok": False, "msg": "engine.html 不存在"}

        url = f"file:///{html_file.as_posix()}#shot={shot_id}"
        webview.create_window(
            title=f"预览 - {shot_id}",
            url=url,
            width=1280,
            height=720,
            js_api=self,
            maximized=True,
        )
        return {"ok": True}

    def save_size(self, shot_id, adjustments):
        """把尺寸数据写进分镜的 mg_config_size.json"""
        shot_dir = SHOTS_ROOT / shot_id
        if not shot_dir.exists():
            return {"ok": False, "msg": "分镜不存在"}

        size_file = shot_dir / "mg_config_size.json"
        size_file.write_text(
            json.dumps(adjustments, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        return {"ok": True}

    def get_shot_materials(self, shot_id):
        """返回当前分镜三样材料齐不齐"""
        shot_dir = SHOTS_ROOT / shot_id

        script_ok = False
        sf = shot_dir / "script.txt"
        if sf.exists() and sf.read_text(encoding="utf-8").strip():
            script_ok = True

        video_ok = bool(list(shot_dir.glob("VID_*.mp4")))
        config_ok = (shot_dir / "mg_config.js").exists()

        return {
            "script": script_ok,
            "video": video_ok,
            "config": config_ok,
        }

    def render_shot(self, shot_id):
        """生成分镜视频：后台线程跑 5 个脚本"""
        shot_dir = SHOTS_ROOT / shot_id
        if not shot_dir.exists():
            return {"ok": False, "msg": "分镜不存在"}

        sf = shot_dir / "script.txt"
        if not sf.exists() or not sf.read_text(encoding="utf-8").strip():
            return {"ok": False, "msg": "文案为空"}
        if not list(shot_dir.glob("VID_*.mp4")):
            return {"ok": False, "msg": "没有视频"}
        if not (shot_dir / "mg_config.js").exists():
            return {"ok": False, "msg": "没有配置文件"}

        threading.Thread(target=self._render_worker, args=(shot_id,), daemon=True).start()
        return {"ok": True}

    def _render_worker(self, shot_id):
        try:
            shot_dir = SHOTS_ROOT / shot_id

            self._push_js("setPreparing()")

            export_audio.main()
            audio_to_timestamp.main()
            match_shots.main()

            def cb(ratio):
                pct = ratio * 99
                self._push_js(f"setProgress({pct})")

            render_frames.set_progress_callback(cb)
            render_frames.main()
            render_frames.set_progress_callback(None)

            compose_video.main()

            # 把所有已生成的分镜视频复制到根目录，改名
            for sd in SHOTS_ROOT.iterdir():
                if sd.is_dir() and sd.name.startswith("shot_"):
                    f = sd / "final.mp4"
                    if f.exists():
                        dest = WORKSPACE_ROOT / f"{sd.name}_分镜音画同步视频.mp4"
                        shutil.copy(f, dest)

            self._push_js("setProgress(100)")
            self._push_js("onRenderDone()")

        except Exception as e:
            import traceback
            traceback.print_exc()
            self._push_js(f"onRenderError({json.dumps(str(e))})")

    def _open_player(self, shot_id):
        video_file = SHOTS_ROOT / shot_id / "final.mp4"
        if not video_file.exists():
            return
        player_html = RES_DIR / "web" / "player.html"
        url = f"file:///{player_html.as_posix()}#video={video_file.as_posix()}"
        webview.create_window(
            title=f"分镜视频 - {shot_id}",
            url=url,
            width=960,
            height=640,
        )

    def _full_video_worker(self):
        try:
            self._push_js("setPreparing()")

            concat_shots.main()

            # 1. 把 full_video.mp4 重命名为 final_video_最终完整音画同步视频.mp4
            old_full = WORKSPACE_ROOT / "full_video.mp4"
            new_full = WORKSPACE_ROOT / "final_video_最终完整音画同步视频.mp4"
            if old_full.exists():
                if new_full.exists():   # 如果之前生成过，先删旧的，避免重名报错
                    new_full.unlink()
                old_full.rename(new_full)

            # 2. 循环把分镜视频复制到根目录，改名
            import shutil
            for shot_dir in SHOTS_ROOT.iterdir():
                if shot_dir.is_dir() and shot_dir.name.startswith("shot_"):
                    final_mp4 = shot_dir / "final.mp4"
                    if final_mp4.exists():
                        dest = WORKSPACE_ROOT / f"{shot_dir.name}_分镜音画同步视频.mp4"
                        shutil.copy(final_mp4, dest)

            self._push_js("setProgress(100)")
            self._push_js("onRenderDone()")

        except Exception as e:
            import traceback
            traceback.print_exc()
            self._push_js(f"onRenderError({json.dumps(str(e))})")

    def generate_full_video(self):
        """生成完整视频：后台线程跑拼接"""
        threading.Thread(target=self._full_video_worker, daemon=True).start()
        return {"ok": True}       

    def open_workspace(self):
        """打开 workspace 文件夹"""
        import os
        os.startfile(str(WORKSPACE_ROOT))
        return {"ok": True} 

    def read_clipboard(self):
        """读剪贴板内容，返回给前端"""
        return get_clipboard_text()

    def check_archive_ready(self):
        """检查能不能归档（只看有没有最终视频）"""
        final_video = WORKSPACE_ROOT / "final_video_最终完整音画同步视频.mp4"
        if not final_video.exists():
            return {"ok": False, "msg": "项目还没完成（没有最终完整视频），不能归档"}
        return {"ok": True}

    def archive_workspace(self, folder_name):
        """归档：把 workspace 内容移到 archives/自定义名/，然后重建 workspace"""
        final_video = WORKSPACE_ROOT / "final_video_最终完整音画同步视频.mp4"
        if not final_video.exists():
            return {"ok": False, "msg": "项目还没完成，不能归档"}

        if not folder_name or not folder_name.strip():
            return {"ok": False, "msg": "文件夹名不能为空"}

        # 去掉非法字符
        safe_name = folder_name.strip()
        for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
            safe_name = safe_name.replace(ch, '_')

        archive_dir = BASE_DIR / "archives" / safe_name
        if archive_dir.exists():
            return {"ok": False, "msg": "同名归档已存在，请换个名字"}

        archive_dir.mkdir(parents=True, exist_ok=True)

        # 把 workspace 里的东西挪进去
        for item in WORKSPACE_ROOT.iterdir():
            shutil.move(str(item), str(archive_dir / item.name))

        # 重建 workspace/shots/shot_01
        SHOTS_ROOT.mkdir(parents=True, exist_ok=True)
        create_shot("shot_01")

        return {"ok": True, "archive": safe_name}

    def open_manual(self):
        """打开说明书窗口"""
        manual_html = RES_DIR / "web" / "manual.html"
        if not manual_html.exists():
            return {"ok": False, "msg": "说明书文件不存在"}
        webview.create_window(
            title="使用说明书",
            url=f"file:///{manual_html.as_posix()}",
            width=900,
            height=800,
            maximized=True,
        )
        return {"ok": True}

    def open_feedback(self):
        """打开 Gitee 反馈页"""
        import webbrowser
        webbrowser.open("https://gitee.com/learning-ai-with-bai-qiang/mg-tool/issues/new")
        return {"ok": True}
        
# ================= 启动 =================

def main():
    ensure_workspace()

    api = Api()
    webview.create_window(
        title="MG 动画工具",
        url=f"file:///{INDEX_HTML.as_posix()}",
        width=1280,
        height=800,
        resizable=True,
        js_api=api,
        maximized=True,
    )
    webview.start()

if __name__ == "__main__":
    main()