# match_shots.py - 匹配镜头开始时间，往 config 里填 start_time
import json
import re
from pathlib import Path

# ================= 路径配置 =================
from paths import workspace_path   # ← ① 新增

SHOTS_ROOT = workspace_path("shots")   # ← ② 改动

# ================= 通用工具函数 =================
# ↓↓↓ 以下到 write_start_times_to_config 结束，一个字没动 ↓↓↓

def clean_text(text):
    """去掉所有空格、标点、特殊符号，只保留汉字、字母、数字"""
    return re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', text)


def extract_voice_texts_from_config(config_path):
    """从 config.js 中提取每个镜头的 voice_text 字段"""
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = r'voice_text\s*:\s*["\']([^"\']+)["\']'
    return re.findall(pattern, content)


def find_shot_starts(timestamp_path, voice_texts):
    """根据每段台词前6个字，在时间戳中定位镜头开始时间"""
    with open(timestamp_path, 'r', encoding='utf-8') as f:
        words = json.load(f)

    full_text = ''
    word_positions = []
    word_starts = []

    for w in words:
        cleaned = clean_text(w['text'])
        if cleaned:
            word_positions.append(len(full_text))
            full_text += cleaned
            word_starts.append(w['start'])

    shot_starts = []
    search_from = 0

    for vt in voice_texts:
        cleaned_vt = clean_text(vt)
        if len(cleaned_vt) < 6:
            print(f"⚠️ 台词太短，无法取前6个字：{vt}")
            continue

        anchor = cleaned_vt[:6]
        pos = full_text.find(anchor, search_from)

        if pos == -1:
            print(f"⚠️ 未找到台词片段：{vt}")
            continue

        word_idx = 0
        for i, wp in enumerate(word_positions):
            if wp >= pos:
                word_idx = i
                break

        shot_starts.append(word_starts[word_idx])
        search_from = pos + len(anchor)

    return shot_starts


def write_start_times_to_config(config_path, shot_starts):
    """把 start_time 写回 config.js 的每个镜头"""
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()

    start_time_pattern = r'start_time\s*:\s*[^,]+'
    matches = list(re.finditer(start_time_pattern, content))

    if len(matches) < len(shot_starts):
        print(f"⚠️ config.js 中 start_time 字段数量({len(matches)})少于镜头数({len(shot_starts)})")
        return

    new_content = content
    for i in range(len(shot_starts) - 1, -1, -1):
        match = matches[i]
        replacement = f'start_time: {shot_starts[i]}'
        new_content = new_content[:match.start()] + replacement + new_content[match.end():]

    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"✅ 已写入 {len(shot_starts)} 个 start_time 到 config.js")


# ================= 主流程 =================

def main():                                       # ← ③ 新增：把原来 __main__ 里的那坨搬进来
    if not SHOTS_ROOT.exists():
        print(f"❌ 找不到目录：{SHOTS_ROOT}")
        return                                    # ← 注意：原来这里是 else，现在改成 return

    shot_dirs = sorted([d for d in SHOTS_ROOT.iterdir() if d.is_dir() and d.name.startswith("shot_")])

    if not shot_dirs:
        print(f"⚠️ {SHOTS_ROOT} 下没有 shot_* 文件夹")
        return                                    # ← 同上

    print(f"📂 找到 {len(shot_dirs)} 个分镜")

    for shot_dir in shot_dirs:
        shot_id = shot_dir.name
        config_file = shot_dir / "mg_config.js"
        timestamp_file = shot_dir / "timestamps.json"

        print(f"\n🎬 处理：{shot_id}")

        if not config_file.exists():
            print(f"   ⚠️ 找不到 mg_config.js，跳过")
            continue
        if not timestamp_file.exists():
            print(f"   ⚠️ 找不到 timestamps.json，跳过")
            continue

        content = config_file.read_text(encoding="utf-8")
        values = re.findall(r'start_time\s*:\s*([\d.]+)', content)
        if values and all(float(v) != 0 for v in values):
            print(f"   ⏭️ start_time 已填过，跳过")
            continue

        voice_texts = extract_voice_texts_from_config(config_file)
        if not voice_texts:
            print(f"   ❌ config 里没有 voice_text")
            continue

        shot_starts = find_shot_starts(timestamp_file, voice_texts)

        if len(shot_starts) == len(voice_texts):
            write_start_times_to_config(config_file, shot_starts)
        else:
            print(f"   ❌ 数量不一致：台词{len(voice_texts)}段，找到{len(shot_starts)}个时间")


if __name__ == "__main__":                        # ← ③ 新增
    main()