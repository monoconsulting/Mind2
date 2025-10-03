from services.file_detection import detect_file


def test_detects_pdf_from_header():
    sample_pdf = b"%PDF-1.4\nTest" + b"0" * 20
    result = detect_file(sample_pdf, "document.bin")
    assert result.kind == "pdf"
    assert result.mime_type == "application/pdf"


def test_detects_png_image():
    # Minimal PNG header with IHDR chunk
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01"
        b"\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00"
        b"\x90wS\xde"
        b"\x00\x00\x00\x0cIDAT"
        b"\x08\xd7c\xf8\xff\xff?\x00\x05\xfe\x02\xfe"
        b"A\x89\x1f\x0f"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    result = detect_file(png_bytes, "image.png")
    assert result.kind == "image"
    assert result.mime_type in {"image/png", None}


def test_detects_wav_audio():
    wav_bytes = (
        b"RIFF" + b"\x24\x08\x00\x00" + b"WAVE"
        + b"fmt " + b"\x10\x00\x00\x00" + b"\x01\x00\x01\x00"
        + b"\x40\x1f\x00\x00" + b"\x80>\x00\x00" + b"\x02\x00\x10\x00"
    )
    result = detect_file(wav_bytes, "audio.wav")
    assert result.kind == "audio"
    assert result.mime_type in {"audio/wav", "audio/x-wav"}
