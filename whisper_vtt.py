"""Transcribe an audio file to a .vtt with faster-whisper.

Kept standalone on purpose: main.py imports it for the "local" backend, and
the ssh/docker helper copies it to another machine and runs it there.

usage: python whisper_vtt.py AUDIO OUT.vtt [--model small] [--device auto] [--compute-type default] [--language en]
"""
import argparse
import sys


def _timestamp(sec):
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


def transcribe(audio, out, model="small", device="auto", compute_type="default", language=None):
    from faster_whisper import WhisperModel

    print(f"loading whisper model '{model}' ({device}, {compute_type})", file=sys.stderr)
    whisper = WhisperModel(model, device=device, compute_type=compute_type)
    segments, info = whisper.transcribe(audio, language=language or None, vad_filter=True)

    # segments is a generator, the actual work happens as we iterate
    with open(out, "w") as f:
        f.write("WEBVTT\n\n")
        for seg in segments:
            f.write(f"{_timestamp(seg.start)} --> {_timestamp(seg.end)}\n{seg.text.strip()}\n\n")
            print(f"\rtranscribed {seg.end / info.duration:.0%}", end="", file=sys.stderr, flush=True)
    print(file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe audio to WebVTT with faster-whisper")
    parser.add_argument("audio")
    parser.add_argument("out")
    parser.add_argument("--model", default="small", help="faster-whisper model name or local path")
    parser.add_argument("--device", default="auto", help="auto | cpu | cuda")
    parser.add_argument("--compute-type", default="default", help="e.g. int8, float16, default")
    parser.add_argument("--language", default=None, help="e.g. en (blank = auto-detect)")
    a = parser.parse_args()
    transcribe(a.audio, a.out, a.model, a.device, a.compute_type, a.language)
