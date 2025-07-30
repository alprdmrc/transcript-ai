from pathlib import Path
import httpx
from urllib.parse import urlparse

# VERY simple allowlist; expand later (SAS links, S3, etc.)
ALLOWED_HOSTS = {"humanaswhisperxfilestest.blob.core.windows.net"}

def _check_allowlist(url: str) -> None:
    host = urlparse(url).hostname or ""
    if host not in ALLOWED_HOSTS:
        raise ValueError(f"URL host not allowed: {host}")

def download_to_tmp(url: str, job_id: str, tmp_dir: Path = Path("data/tmp")) -> Path:
    _check_allowlist(url)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    target = tmp_dir / f"{job_id}"
    with httpx.stream("GET", url, timeout=60) as r:
        r.raise_for_status()
        with open(target, "wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    return target


## https://humanaswhisperxfilestest.blob.core.windows.net/audiofiles/sampleaudio.mp4