#!/bin/zsh
# probe.sh: one line per clip so the plan starts from facts, not guesses.
#   probe.sh <footage folder or files...> > job/footage-log.md
# Columns: file, seconds, size, fps, HDR or SDR, audio. HDR (HLG or PQ) must go through
# proxies.sh before cut.py will take it. Add your own notes column by hand: best moments by timecode.
echo "| file | s | size | fps | range | audio | notes |"
echo "|---|---|---|---|---|---|---|"
files=()
for a in "$@"; do
  if [ -d "$a" ]; then files+=("$a"/*.(mov|MOV|mp4|MP4|m4v|M4V)(N)); else files+=("$a"); fi
done
for f in $files; do
  j=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,color_transfer:stream_side_data=rotation:format=duration -of json "$f")
  a=$(ffprobe -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 "$f" | grep -m1 audio || true)
  python3 -c "
import json,sys
from fractions import Fraction
j=json.loads(sys.argv[1]); s=j['streams'][0]; w,h=s['width'],s['height']
rot=[d.get('rotation',0) for d in s.get('side_data_list',[]) or []]
if rot and abs(int(rot[0])) in (90,270): w,h=h,w
trc=s.get('color_transfer','?'); rng='HDR (convert)' if trc in ('arib-std-b67','smpte2084') else 'SDR'
print(f\"| {sys.argv[2]} | {float(j['format']['duration']):.1f} | {w}x{h} | {float(Fraction(s['r_frame_rate'])):.0f} | {rng} | {'yes' if sys.argv[3] else 'no'} |  |\")
" "$j" "${f:t}" "$a"
done
