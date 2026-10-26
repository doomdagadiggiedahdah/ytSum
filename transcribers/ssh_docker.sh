#!/bin/bash

# Run whisper_vtt.py on another machine over ssh, inside a docker image that has faster-whisper.
# Meant to be used as the "command" transcribe backend in config.toml.
#
# usage: ssh_docker.sh HOST IMAGE MODEL AUDIO OUT [LANGUAGE]
#   HOST   ssh target, e.g. me@my-gpu-box
#   IMAGE  docker image with faster-whisper installed
# The remote's ~/.cache/huggingface is mounted so models only download once.
# Extra docker flags (e.g. "--runtime nvidia") can be passed via YTSUM_DOCKER_ARGS.

set -euo pipefail

host=$1 image=$2 model=$3 audio=$4 out=$5 lang=${6:-}
here="$(dirname "$(readlink -f "$0")")"

remote=$(ssh "$host" mktemp -d)
trap 'ssh "$host" rm -rf "$remote"' EXIT

scp -q "$audio" "$here/../whisper_vtt.py" "$host:$remote/"

# $HOME is single-quoted so it expands on the remote, not here
ssh "$host" docker run --rm ${YTSUM_DOCKER_ARGS:-} \
    -v "$remote:/work" -v '$HOME/.cache/huggingface:/hf' -e HF_HOME=/hf \
    --entrypoint python3 "$image" \
    /work/whisper_vtt.py "/work/$(basename "$audio")" /work/out.vtt --model "$model" ${lang:+--language "$lang"}

scp -q "$host:$remote/out.vtt" "$out"
