"""
run_pipeline.py —— 一键自动执行完整流程
用法：本地 python run_pipeline.py；打包后由 app.py 直接调 main()
功能（依次执行 6 个脚本）：
1. export_audio.py        从视频提取音频
2. audio_to_timestamp.py  生成时间戳
3. match_shots.py         匹配 start_time
4. render_frames.py       逐帧渲染
5. compose_video.py       合成 final.mp4
6. concat_shots.py        拼接完整视频
"""
import sys

# ================= 导入 6 个子脚本 =================
from paths import workspace_path
import export_audio
import audio_to_timestamp
import match_shots
import render_frames
import compose_video
import concat_shots


# ================= 执行单步 =================

def run_step(step_name, func):
    """执行一个步骤，出错就停"""
    print(f"\n{'='*60}")
    print(f"▶️  步骤：{step_name}")
    print(f"{'='*60}")
    try:
        func()
    except Exception as e:
        print(f"\n❌ {step_name} 失败：{e}")
        return False
    print(f"✅ {step_name} 完成")
    return True


# ================= 主流程 =================

def main():
    print("🚀 开始自动执行 MG 动画全流程")

    steps = [
        ("1/6 提取音频",              export_audio.main),
        ("2/6 生成时间戳",            audio_to_timestamp.main),
        ("3/6 匹配镜头开始时间",       match_shots.main),
        ("4/6 直接生成无声视频",       render_frames.main),
        ("5/6 逐个分镜合成音画同步视频", compose_video.main),
        ("6/6 合成完整音画同步视频",    concat_shots.main),
    ]

    for name, func in steps:
        if not run_step(name, func):
            print(f"\n❌ 流程终止于：{name}")
            return

    print(f"\n{'='*60}")
    print("🎉 全流程执行完成！")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()