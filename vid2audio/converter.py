"""Core video → audio extraction logic."""

from pathlib import Path
from typing import Optional, Tuple
import json
import subprocess

SUPPORTED_VIDEO = {
    ".mp4", ".mkv", ".avi", ".mov", ".webm",
    ".flv", ".wmv", ".m4v", ".ts", ".mpg", ".mpeg",
}

AUDIO_CODECS = {
    "mp3":  {"codec": "libmp3lame", "ext": ".mp3"},
    "aac":  {"codec": "aac",        "ext": ".m4a"},
    "opus": {"codec": "libopus",    "ext": ".opus"},
    "flac": {"codec": "flac",       "ext": ".flac"},
    "wav":  {"codec": "pcm_s16le",  "ext": ".wav"},
    "ogg":  {"codec": "libvorbis",  "ext": ".ogg"},
    "copy": {"codec": "copy",       "ext": None},
}

def _probe(input_path: Path) -> dict:
    """Run ffprobe and return parsed JSON."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(input_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)

def _detect_audio_ext(probe_data: dict) -> str:
    """Guess a sane extension when codec is 'copy'."""
    for stream in probe_data.get("streams", []):
        if stream.get("codec_type") != "audio":
            continue
        name = stream.get("codec_name", "")
        if "aac" in name:
            return ".m4a"
        if "mp3" in name or "mp2" in name:
            return ".mp3"
        if "opus" in name:
            return ".opus"
        if "vorbis" in name:
            return ".ogg"
        if "flac" in name:
            return ".flac"
        if "pcm" in name:
            return ".wav"
    return ".mka"

def _resolve_output_path(
    input_path: Path,
    output_dir: Optional[Path],
    ext: str,
) -> Path:
    dest_dir = output_dir if output_dir else input_path.parent
    dest_dir.mkdir(parents=True, exist_ok=True)
    return dest_dir / (input_path.stem + ext)

def get_audio_info(input_path: Path) -> dict:
    """Return audio stream metadata from a video file."""
    probe = _probe(input_path)
    for stream in probe.get("streams", []):
        if stream.get("codec_type") == "audio":
            return {
                "codec": stream.get("codec_name"),
                "sample_rate": stream.get("sample_rate"),
                "channels": stream.get("channels"),
                "bitrate": stream.get("bit_rate"),
                "duration": probe.get("format", {}).get("duration"),
            }
    raise ValueError(f"No audio stream found in {input_path}")

def extract_audio(
    input_path: Path,
    output_dir: Optional[Path] = None,
    audio_format: str = "mp3",
    bitrate: Optional[str] = None,
    sample_rate: Optional[int] = None,
    channels: Optional[int] = None,
    volume: Optional[float] = None,
    start: Optional[str] = None,
    duration: Optional[str] = None,
    overwrite: bool = False,
) -> Tuple[Path, int, int]:
    """
    Extract audio from a video file.

    Returns (output_path, video_bytes, audio_bytes).
    """
    if input_path.suffix.lower() not in SUPPORTED_VIDEO:
        raise ValueError(f"Unsupported format: {input_path.suffix}")

    codec_info = AUDIO_CODECS.get(audio_format)
    if not codec_info:
        raise ValueError(
            f"Unknown audio format '{audio_format}'. "
            f"Supported: {', '.join(AUDIO_CODECS)}"
        )

    probe = _probe(input_path)
    ext = codec_info["ext"] or _detect_audio_ext(probe)
    output_path = _resolve_output_path(input_path, output_dir, ext)

    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"Output already exists: {output_path}  (use --overwrite)"
        )

    video_bytes = input_path.stat().st_size

    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error"]

    if start:
        cmd += ["-ss", start]
    if duration:
        cmd += ["-t", duration]

    cmd += ["-i", str(input_path), "-vn"]

    cmd += ["-acodec", codec_info["codec"]]

    if codec_info["codec"] != "copy":
        if bitrate:
            cmd += ["-b:a", bitrate]
        if sample_rate:
            cmd += ["-ar", str(sample_rate)]
        if channels:
            cmd += ["-ac", str(channels)]

    # Volume filter (e.g. 1.5 = +50%, 0.5 = -50%)
    if volume and codec_info["codec"] != "copy":
        cmd += ["-af", f"volume={volume}"]

    if overwrite:
        cmd.append("-y")

    cmd.append(str(output_path))

    subprocess.run(cmd, check=True)

    audio_bytes = output_path.stat().st_size
    return output_path, video_bytes, audio_bytes