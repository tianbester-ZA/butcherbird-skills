#!/bin/bash
# composite.sh <clean.mp4> <framesdir> <out.mp4> [crop "w:h:x:y"]
# Overlays transparent PNG frames (f%05d.png, same fps as the master) on the clean master; audio copied untouched.
set -e
CLEAN="$1"; FR="$2"; OUT="$3"; CROP="$4"
FPS=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 "$CLEAN")
if [ -n "$CROP" ]; then FILT="[0:v][1:v]overlay=0:0:format=auto,crop=$CROP,format=yuv420p"; else FILT="[0:v][1:v]overlay=0:0:format=auto,format=yuv420p"; fi
ffmpeg -nostdin -v error -y -i "$CLEAN" -framerate "$FPS" -i "$FR/f%05d.png" -filter_complex "$FILT" -map 0:a -c:a copy -c:v libx264 -crf 15 -preset slow -profile:v high -level 4.2 -bsf:v h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1 -movflags +faststart -shortest "$OUT"
ffprobe -v error -show_entries format=duration:stream=width,height,codec_name -of compact "$OUT"
