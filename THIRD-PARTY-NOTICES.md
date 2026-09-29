# 第三方组件声明 / Third-Party Notices

本项目（MG 动画工具）自身源码采用 MIT 协议发布。

分发包中包含了以下第三方组件，它们各自遵循独立的许可证，**不属于 MIT 协议范围**。
本项目对它们的打包方式，仅限"原样分发"或"外部进程调用"，未修改其源码、未静态链接进本项目主程序。

---

## 1. Chromium（通过 Playwright 分发）

- **用途**：视频渲染时用于逐帧截图
- **许可证**：BSD-3-Clause（内含部分 MIT / Apache-2.0 等第三方子组件）
- **版权**：Copyright The Chromium Authors
- **源码获取**：https://chromium.googlesource.com/chromium/src/
- **分发方式**：本项目分发包内包含 Playwright 下载的 Chromium 构建版，保持原始文件结构，未做修改。

---

## 2. Playwright

- **用途**：驱动 Chromium 进行无头浏览器渲染
- **许可证**：Apache License 2.0
- **版权**：Copyright Microsoft Corporation
- **源码获取**：https://github.com/microsoft/playwright
- **分发方式**：本项目分发包内包含 Playwright 及其附带的浏览器驱动文件，未做修改。

---

## 3. FFmpeg

- **版本**：N-126905-gb87602a63a-20260927
- **用途**：音频提取、视频合成、片段拼接
- **许可证**：GNU Lesser General Public License v2.1 (LGPL-2.1)
- **源码获取**：https://ffmpeg.org/
- **分发方式**：本项目分发包内附带 FFmpeg 官方构建的可执行文件（`ffmpeg.exe`、`ffprobe.exe`）。
  本项目**仅通过外部进程方式调用** FFmpeg，**未将其静态链接进主程序**，因此 LGPL 的传染性义务不适用于本项目源码。

---

## 4. Microsoft Edge WebView2 Runtime

- **用途**：用于显示工具界面（PyWebView 依赖）
- **许可证**：Microsoft WebView2 Runtime License Terms
- **许可页面**：https://learn.microsoft.com/en-us/microsoft-edge/webview2/eula
- **分发方式**：本项目**未内嵌 WebView2 Runtime 二进制文件**。
  程序运行时若检测到系统缺失 WebView2，会提示用户前往微软官方页面自行下载安装。
  是否安装由用户决定，本项目不代用户安装、也不修改系统组件。

---

## 5. Microsoft Visual C++ Redistributable

- **用途**：Windows 系统运行依赖库（PyTorch 等底层组件所需）
- **许可证**：Microsoft Visual C++ Redistributable License Terms
- **版权**：Copyright Microsoft Corporation
- **分发方式**：本项目分发包内附带微软官方原版 `VC_redist.x64.exe`，未做任何修改。
  程序首次运行时，若检测到系统缺失该运行库，会静默调用该安装器进行安装。
  该文件的所有权利归 Microsoft Corporation 所有，遵循微软自身的许可条款。

---

## 6. 其他 Python 依赖库

本项目还使用了以下开源库，完整许可证文本可在各项目官方仓库查阅：

- **PyWebView** — BSD-3-Clause
- **stable-ts** — MIT
- **OpenAI Whisper** — MIT
- **PyTorch** — BSD-3-Clause
- **pyperclip** — BSD-3-Clause
- **PyInstaller** — GPL 2.0 with Bootloader Exception

> 关于 PyInstaller 的说明：PyInstaller 本体采用 GPL 2.0 协议，但其 **bootloader 附带特殊例外条款**，
> 明确允许使用它打包的程序**不因此被传染为 GPL**。因此，本项目源码仍完全遵循 MIT 协议发布。

---

## 说明

以上第三方组件的版权归各自所有者所有。
本项目仅在其各自许可范围内进行分发和调用，未对上述组件进行任何修改。
如对上述声明有疑问，请联系对应组件的官方维护方。