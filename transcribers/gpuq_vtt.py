#!/usr/bin/env python3
"""Transcribe through a gpu-queued daemon and write a .vtt.
Meant to be used as the "command" transcribe backend in config.toml.

usage: gpuq_vtt.py GPUQ_DIR AUDIO OUT [LANGUAGE]
  GPUQ_DIR  folder containing gpuq.py (the gpu-queued client)

The whisper model is whatever the gpu-queued workers are configured with, so {model} doesn't apply here.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from whisper_vtt import _timestamp

gpuq_dir, audio, out = sys.argv[1:4]
language = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else None

sys.path.insert(0, os.path.expanduser(gpuq_dir))
import gpuq

options = {"language": language} if language else {}
segments = []
for msg in gpuq.stream(audio, priority="batch", options=options):
    event = msg.get("event")
    if event == "queued":
        print(f"\rqueued (position {msg.get('position')})", end="", file=sys.stderr, flush=True)
    elif event == "segment":
        segments.append(msg)
        print(f"\rtranscribed up to {msg['end'] / 60:.1f} min", end="", file=sys.stderr, flush=True)
    elif event == "error":
        sys.exit(f"\ngpu-queued error: {msg.get('error')}")
print(file=sys.stderr)

with open(out, "w") as f:
    f.write("WEBVTT\n\n")
    for seg in segments:
        f.write(f"{_timestamp(seg['start'])} --> {_timestamp(seg['end'])}\n{seg['text'].strip()}\n\n")
