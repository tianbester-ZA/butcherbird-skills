#!/bin/zsh
# sheet.sh: pictures of a cut for the critic and for the person running this.
#   sheet.sh <video.mp4> [strip_start_s] [strip_len_s] [out_dir]
# Writes next to the video, or into out_dir (use it for source clips: footage is never written beside):
#   <stem>-sheet.jpg   40 frames evenly spread, 8 x 5, in reading order (times in <stem>-sheet.txt)
#   <stem>-strip.jpg   10 fps strip of a window (default the first 3 s, the hook), 10 per row
#   <stem>-frame0.png  frame 0 at full size (the thumbnail the feed shows before play)
# No drawtext on this ffmpeg, so frame times go in the .txt beside the sheet.
set -e
v="$1"; [ -f "$v" ] || { echo "usage: sheet.sh video.mp4 [strip_start] [strip_len] [out_dir]"; exit 2; }
ss="${2:-0}"; sl="${3:-3}"
d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$v")
wh=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$v" | head -1)
w=${wh%,*}; h=${wh#*,}
tw=216; th=$(( 216 * h / w / 2 * 2 ))
stem="${v%.*}"
if [ -n "$4" ]; then mkdir -p "$4"; b="${v:t}"; stem="$4/${b%.*}"; fi
# 40 evenly spaced frames: one in the middle of each 1/40th of the cut
rate=$(python3 -c "print(40/($d*0.985))")
ffmpeg -nostdin -v error -y -i "$v" -vf "fps=${rate}:start_time=$(python3 -c "print($d/80)"),scale=$tw:$th,tile=8x5:padding=4:margin=4:color=0x202020" -frames:v 1 -q:v 3 "$stem-sheet.jpg"
python3 -c "
d=$d
print('sheet frames, left to right, top to bottom (seconds):')
t=[round(d/80+i*d*0.985/40,2) for i in range(40)]
for r in range(5): print('  row', r+1, ' '.join(f'{x:6.2f}' for x in t[r*8:r*8+8]))" > "$stem-sheet.txt"
n=$(python3 -c "import math;print(math.ceil($sl*10/10))")
ffmpeg -nostdin -v error -y -ss "$ss" -t "$sl" -i "$v" -vf "fps=10,scale=144:-2,tile=10x$n:padding=2:color=0x202020" -frames:v 1 -q:v 3 "$stem-strip.jpg"
ffmpeg -nostdin -v error -y -i "$v" -frames:v 1 "$stem-frame0.png"
echo "$stem-sheet.jpg"; echo "$stem-strip.jpg"; echo "$stem-frame0.png"; cat "$stem-sheet.txt"
