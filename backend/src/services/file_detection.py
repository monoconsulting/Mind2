"""Utilities for detecting uploaded file types."""
from __future__ import annotations

import io
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from PIL import Image


DetectedKind = Literal["image", "pdf", "audio", "other"]


@dataclass(slots=True)
class DetectedFile:
    """Describes the detected file metadata."""

    kind: DetectedKind
    mime_type: Optional[str]
    extension: str


_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
_IMAGE_MIME_PREFIX = "image/"
_AUDIO_MIME_PREFIX = "audio/"


def _detect_pdf(data: bytes, extension: str) -> Optional[DetectedFile]:
    if data.startswith(b"%PDF-"):
        return DetectedFile("pdf", "application/pdf", ".pdf")
    if extension == ".pdf":
        return DetectedFile("pdf", "application/pdf", ".pdf")
    return None


def _detect_image(data: bytes, extension: str) -> Optional[DetectedFile]:
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
            mime = Image.MIME.get(img.format)
            ext = f".{img.format.lower()}" if img.format else extension
            return DetectedFile("image", mime, ext or extension)
    except Exception:
        pass

    return None


def _detect_audio(data: bytes, extension: str, mime_guess: Optional[str]) -> Optional[DetectedFile]:
    header = data[:16]
    if header.startswith(b"ID3") or header[0:2] == b"\xff\xfb":
        return DetectedFile("audio", "audio/mpeg", extension or ".mp3")
    if header.startswith(b"RIFF") and data[8:12] == b"WAVE":
        return DetectedFile("audio", "audio/wav", extension or ".wav")
    if header[4:8] == b"ftyp":
        # Likely AAC/M4A container
        return DetectedFile("audio", mime_guess or "audio/mp4", extension or ".m4a")
    if extension in _AUDIO_EXTENSIONS:
        return DetectedFile("audio", mime_guess, extension)
    if mime_guess and mime_guess.startswith(_AUDIO_MIME_PREFIX):
        return DetectedFile("audio", mime_guess, extension)
    return None


def detect_file(data: bytes, filename: str) -> DetectedFile:
    """Detect the file type for uploaded content.

    Detection uses file headers when possible and falls back to
    extensions and mimetype guesses.
    """

    extension = Path(filename).suffix.lower()
    mime_guess, _ = mimetypes.guess_type(filename)

    pdf = _detect_pdf(data, extension)
    if pdf:
        return pdf

    image = _detect_image(data, extension)
    if image:
        return image

    audio = _detect_audio(data, extension, mime_guess)
    if audio:
        return audio

    if mime_guess and mime_guess.startswith(_IMAGE_MIME_PREFIX):
        return DetectedFile("image", mime_guess, extension)

    return DetectedFile("other", mime_guess, extension)
