import whisper.audio
import stable_whisper

# 看看 whisper 内部的 load_audio 是哪个
print("whisper.audio.load_audio =", whisper.audio.load_audio)

# 看看 stable_whisper 有没有自己的 load_audio
print("stable_whisper.load_audio =", getattr(stable_whisper, "load_audio", "（没有）"))
print("stable_whisper.audio =", getattr(stable_whisper, "audio", "（没有）"))