from pathlib import Path
import subprocess

def normalize_wav(src: Path, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    # mono, 16 kHz, 16-bit PCM
    cmd = ["ffmpeg", "-y", "-i", str(src), "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le", str(dst)]
    subprocess.run(cmd, check=True, capture_output=True)
    return dst