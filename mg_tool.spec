# mg_tool.spec
# PyInstaller 打包配置

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

project_root = Path(SPECPATH)

# 收集各库的完整资源
datas = []
binaries = []
hiddenimports = []

for pkg in ['stable_whisper', 'whisper', 'playwright', 'webview', 'pyperclip', 'torch', 'torchaudio']:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as e:
        print(f"[spec] 跳过 {pkg}: {e}")

# 手动加上项目资源（放到 EXE 同级）
datas += [
    ('web', 'web'),
    ('assets', 'assets'),
    ('ms-playwright', 'ms-playwright'),
    ('LICENSE', '.'),                      
    ('THIRD-PARTY-NOTICES.md', '.'),    
]

a = Analysis(
    ['app.py'],
    pathex=[str(project_root / 'scripts')],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='mg_tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # 打包后不显示黑色命令行窗口
    icon=None,              # 有图标的话，改成图标路径
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='mg_tool',
)