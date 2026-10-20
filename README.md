# MG 动画工具

> 不用写代码，不用专业工具，新手小白也能借助免费 AI，轻松制作音画同步的 MG 动画视频。

## 这是什么

一个 Windows 桌面工具，帮不会编程的用户，把**一段文案**变成**带配音的动画视频**。

工作流程：
1. 写文案
2. 工具拼接提示词，复制给免费 AI，让 AI 生成动画配置
3. 把配置导入工具
4. 录一段配音（目前仅支持视频）
5. 工具自动合成动画视频
6. 多个分镜拼成完整视频

## 快速使用（普通用户）

1. 去 [发行版页面](https://github.com/learning-ai-with-bai-qiang/mg-tool/releases) 下载最新版 `mg_tool.zip`
2. 解压到任意目录（**路径不要带中文**）
3. 双击 `mg_tool.exe`
4. 第一次启动会弹一个"是否允许更改"的提示，点"是"（安装微软运行库，安全）
5. 按说明书一步步做

详细教程见工具内的 **[查看说明书]**。

## 从源码运行（开发者）

### 环境要求
- Windows 10 / 11
- Python 3.11
- Git

### 步骤

```bash 
git clone https://github.com/learning-ai-with-bai-qiang/Mg-tool.git
cd mg-tool

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 准备 ffmpeg（放到 assets/ffmpeg/bin/ 下）
# 下载 ffmpeg.exe 和 ffprobe.exe 放进去
# 推荐从 https://www.gyan.dev/ffmpeg/builds/ 下载 essentials 版本

# 准备 VC++ 运行库
# 下载 VC_redist.x64.exe 放到 assets/ 下
# https://aka.ms/vs/17/release/vc_redist.x64.exe

# 准备 chromium（Playwright 会用）
playwright install chromium

# 启动
python app.py
打包成 EXE
bash
python build.py
产物在 dist/mg_tool/。

项目结构
text
mg_tool/
├── app.py                  主程序 + PyWebView 桥接
├── build.py                一键打包脚本
├── mg_tool.spec            PyInstaller 配置
├── assets/                 资源（模板、提示词、ffmpeg、VC_redist）
├── scripts/                流水线脚本
│   ├── paths.py            统一路径管理
│   ├── export_audio.py     从视频提取音频
│   ├── audio_to_timestamp.py  生成逐字时间戳
│   ├── match_shots.py      匹配分镜开始时间
│   ├── render_frames.py    逐帧渲染无声视频
│   ├── compose_video.py    音画合成
│   ├── concat_shots.py     拼接完整视频
│   └── run_pipeline.py     一键跑全流程
├── web/                    前端界面
│   ├── index.html          主界面
│   ├── manual.html         使用说明书
│   └── manual_images/      说明书配图
└── workspace/              用户数据（运行时生成）
依赖说明
PyWebView — 界面

Playwright + Chromium — 视频渲染

stable-ts / Whisper — 语音时间戳对齐

FFmpeg — 音视频处理

PyTorch — 运行 Whisper

第三方组件的完整许可声明见 THIRD-PARTY-NOTICES.md。

反馈
使用中遇到问题，请去 Issues 提交。

许可证
本项目源码采用 MIT 协议 开源。

分发包中包含的第三方组件（Chromium、FFmpeg 等）遵循各自独立的许可，详见 THIRD-PARTY-NOTICES.md。
