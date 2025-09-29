# KB Whisper — VS Code Agent Playbook  

This document tells your AI assistant (running in VS Code on your PC) exactly how to **transcribe audio (e.g., MP3)** using the local **Whisper ASR Webservice** or the **KB-Whisper API** you started with Docker. It includes ready-to-run Python snippets, command recipes, and troubleshooting.  > **Endpoints in the provided project** > > - **Webservice (standard Whisper)** — CPU: `http://localhost:9001|9002|9003`, GPU: `http://localhost:9101|9102|9103`   > - **KB-Whisper API (KBLab models)** — CPU: `http://localhost:9201|9202|9203`, GPU: `http://localhost:9301|9302|9303`   > - All services expose `POST /asr` with `multipart/form-data` (`audio_file` field).  ---  ## 0) Requirements for the agent - VS Code with Python 3.10+ available in the workspace. - `pip install requests` (used by the snippets below). - Docker compose stack is already running (see project `README.md`).  ---  ## 1) Decide the target service Pick one URL depending on the model you want to use:  | Model size | Webservice (CPU) | Webservice (GPU) | KB-Whisper API (CPU) | KB-Whisper API (GPU) | |---|---|---|---|---| | small | `http://localhost:9001` | `http://localhost:9101` | `http://localhost:9201` | `http://localhost:9301` | | medium | `http://localhost:9002` | `http://localhost:9102` | `http://localhost:9202` | `http://localhost:9302` | | large | `http://localhost:9003` | `http://localhost:9103` | `http://localhost:9203` | `http://localhost:9303` |  > If the ASR service runs on the **host** and your code runs inside another **container**, use `http://host.docker.internal:<port>` instead of `localhost`.  ---  ## 2) Health check (optional but recommended) Use this before attempting work, to ensure the service is up.  ```python import requests  def asr_is_ready(base_url: str) -> bool:     """Return True if the ASR service appears healthy.     Args:         base_url: Base URL like 'http://localhost:9001'.     Returns:         True if `/docs` or `/healthz` responds with HTTP 200.     """     for path in ("/healthz", "/docs"):         try:             r = requests.get(base_url.rstrip("/") + path, timeout=5)             if r.status_code == 200:                 return True         except Exception:             pass     return False``

---

## 3) Transcribe a single audio file (MP3/WAV/etc.)

`from __future__ import annotations import requests from pathlib import Path from typing import Literal  def transcribe_file(     audio_path: str | Path,     base_url: str,     output: Literal["text","json","srt","vtt","tsv"] = "text",     language: str = "sv",     word_timestamps: bool = False,     vad_filter: bool = False,     timeout_sec: int = 3600, ) -> bytes:     """Send an audio file to the ASR endpoint and return raw response bytes.      Args:         audio_path: Absolute/relative path to the audio file (.mp3, .wav, .m4a, .flac).         base_url: Base URL to the ASR service, e.g., 'http://localhost:9001'.         output: Desired output format. Use 'text' for plain text, 'json' for rich info,             or 'srt'/'vtt'/'tsv' to get subtitle-like formats.         language: Language hint (use 'sv' for Swedish). Improves speed/accuracy.         word_timestamps: If True, request word-level timestamps (supported by faster-whisper).         vad_filter: If True, enable voice activity detection filtering.         timeout_sec: Request timeout in seconds.      Returns:         Raw bytes of the response body. Write to disk as-is.     """     url = base_url.rstrip("/") + "/asr"     params = {"language": language, "output": output}     if word_timestamps:         params["word_timestamps"] = "true"     if vad_filter:         params["vad_filter"] = "true"      audio_path = Path(audio_path)     with audio_path.open("rb") as f:         files = {"audio_file": f}         resp = requests.post(url, params=params, files=files, timeout=timeout_sec)     resp.raise_for_status()     return resp.content`

**Save the result to disk:**

`def save_bytes(data: bytes, out_path: str | Path) -> None:     """Persist bytes to a file path without modification.      Args:         data: Raw bytes returned from the ASR service.         out_path: Desired output file path (extension should match the format).     """     out = Path(out_path)     out.parent.mkdir(parents=True, exist_ok=True)     out.write_bytes(data)`

**End-to-end example:**

`BASE = "http://localhost:9001"  # choose the port for the model you prefer data = transcribe_file("samples/test.mp3", BASE, output="json", language="sv", word_timestamps=True, vad_filter=True) save_bytes(data, "out/transcript.json")`

---

## 4) Batch a whole folder (idempotent and resumable)

``from pathlib import Path from typing import Iterable  def find_audio(root: str | Path, exts: Iterable[str] = (".mp3", ".wav", ".m4a", ".flac")) -> list[Path]:     """Return a list of audio files under 'root' matching the extensions.      Args:         root: Directory to search.         exts: File extensions to include.      Returns:         List of Path objects to process.     """     root = Path(root)     return [p for p in root.rglob("*") if p.suffix.lower() in {e.lower() for e in exts} and p.is_file()]  def batch_transcribe(     in_dir: str | Path,     out_dir: str | Path,     base_url: str,     output_ext: str = ".vtt",     **kwargs, ) -> None:     """Transcribe all audio files in 'in_dir' and write outputs to 'out_dir'.      Args:         in_dir: Folder containing audio files.         out_dir: Destination folder for transcripts.         base_url: ASR base URL to call for each file.         output_ext: One of '.txt', '.json', '.srt', '.vtt', '.tsv' matching the 'output' format.         **kwargs: Extra args forwarded to `transcribe_file` (output, language, etc.).     """     in_dir, out_dir = Path(in_dir), Path(out_dir)     out_dir.mkdir(parents=True, exist_ok=True)      for src in find_audio(in_dir):         dst = out_dir / (src.stem + output_ext)         if dst.exists():             # Skip if already processed; comment out to force overwrite.             continue         data = transcribe_file(src, base_url=base_url, **kwargs)         save_bytes(data, dst)``

**Batch run example:**

`if __name__ == "__main__":     base = "http://localhost:9002"           # medium     batch_transcribe("samples", "out", base_url=base, output_ext=".vtt",                      output="vtt", language="sv", word_timestamps=False, vad_filter=True)`

---

## 5) (Optional) Send transcript to LM Studio and get an answer

`import requests  def chat_lmstudio(model: str, user_text: str, base_url: str = "http://localhost:1234/v1", api_key: str = "lm-studio") -> str:     """Send a chat completion request to a local LM Studio server and return the reply text.      Args:         model: Model identifier loaded in LM Studio (exact name visible in LM Studio).         user_text: Prompt to send.         base_url: LM Studio OpenAI-compatible base URL.         api_key: Placeholder token. LM Studio typically accepts any non-empty value locally.      Returns:         Assistant's reply content as a string.     """     url = base_url.rstrip("/") + "/chat/completions"     headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}     body = {         "model": model,         "messages": [             {"role": "system", "content": "You are a helpful Swedish assistant."},             {"role": "user", "content": user_text},         ],     }     r = requests.post(url, headers=headers, json=body, timeout=120)     r.raise_for_status()     j = r.json()     return j["choices"][0]["message"]["content"]`

---

## 6) Recommended defaults & format guide

- **Language**: `sv` (locks the recognizer to Swedish).
  
- **Output**:
  
    - `text` → plain UTF-8 text.
      
    - `json` → `{ text, segments[], language }` (useful for timestamps / post-processing).
      
    - `srt` / `vtt` → subtitles (write to `.srt` / `.vtt`).
      
    - `tsv` → tab-separated table (`start`, `end`, `text`).
    
- **word_timestamps**: `true` only when you need per-word timing (slightly slower).
  
- **vad_filter**: `true` is often beneficial for noisy audio.
  

---

## 7) Troubleshooting checklist

- **Connection refused** → Start the correct compose file; verify port. Try the health check function.
  
- **Empty/short output** → Remove `word_timestamps` and `vad_filter` to compare. Verify the file is valid (FFmpeg can probe it).
  
- **Slow on CPU** → Switch to GPU compose (RTX 3090), or pick the **small** model.
  
- **n8n cannot reach `localhost`** → Use `http://host.docker.internal:<port>` from inside containers.
  
- **Wrong format on disk** → Ensure you set `output` to match the target extension you write (`.json`, `.srt`, `.vtt`, etc.).
  

---

## 8) Minimal CLI wrapper (optional)

You can drop this file into your workspace as `kbw_cli.py` and run it from VS Code’s terminal.

`#!/usr/bin/env python3 """Simple CLI wrapper around the local ASR service.  Example:     python kbw_cli.py -f samples/test.mp3 --base http://localhost:9001 --format json -o out/transcript.json --timestamps --vad """ import argparse, sys from pathlib import Path  # Reuse functions above by copy/paste or import them if placed in a module. # transcribe_file, save_bytes ...  def main(argv=None) -> int:     p = argparse.ArgumentParser()     p.add_argument("-f", "--file", required=True, help="Audio path (MP3/WAV/...)" )     p.add_argument("--base", default="http://localhost:9001", help="ASR base URL" )     p.add_argument("--format", choices=["text","json","srt","vtt","tsv"], default="text")     p.add_argument("--language", default="sv")     p.add_argument("--timestamps", action="store_true")     p.add_argument("--vad", action="store_true")     p.add_argument("-o", "--out", required=True, help="Output file path" )     a = p.parse_args(argv)     data = transcribe_file(a.file, base_url=a.base, output=a.format, language=a.language, word_timestamps=a.timestamps, vad_filter=a.vad)     out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(data)     print(out.resolve())     return 0  if __name__ == "__main__":     raise SystemExit(main())`

---

## 9) Safety & data handling

- All processing is **local**. The agent must **not** upload audio or transcripts to external services unless explicitly instructed.
  
- Keep transcripts in your project folder (`out/` by default) and commit only what you need.
  

---

**You’re ready.** The agent can now: check readiness → post MP3 to `/asr` → save transcript → (optionally) forward text to LM Studio.