#!/bin/zsh
# proxies.sh: SDR working copies, 1080 on the short side, H.264, source frame rate.
#   proxies.sh <out_dir> <clips...>
# HDR iPhone footage (HLG or PQ) goes through Apple's avconvert first: it tone-maps to SDR the
# way Photos does, which is the iPhone look we want (no grade on top). SDR goes straight
# to ffmpeg. Finals can be cut from these when the source is 1080p-class; for 4K sources keep the
# proxies for the rough cut and point the final EDL at full-res SDR files made the same way.
set -e
out="$1"; shift; mkdir -p "$out"
for f in "$@"; do
  b="${f:t:r}"; o="$out/$b.mp4"; [ -s "$o" ] && { echo "have $o"; continue; }
  trc=$(ffprobe -v error -select_streams v:0 -show_entries stream=color_transfer -of default=nw=1:nk=1 "$f")
  src="$f"
  if [[ "$trc" == arib-std-b67 || "$trc" == smpte2084 ]]; then
    src="$out/.$b.sdr.mov"
    avconvert --source "$f" --output "$src" --preset PresetHighestQuality --replace >/dev/null
    t2=$(ffprobe -v error -select_streams v:0 -show_entries stream=color_transfer -of default=nw=1:nk=1 "$src")
    [[ "$t2" == arib-std-b67 || "$t2" == smpte2084 ]] && { echo "still HDR after avconvert: $f"; exit 1; }
  fi
  pf=$(ffprobe -v error -select_streams v:0 -show_entries stream=pix_fmt -of default=nw=1:nk=1 "$src")
  r="in_range=tv:out_range=tv"; [[ "$pf" == yuvj* ]] && r="in_range=full:out_range=tv"
  ffmpeg -nostdin -v error -y -i "$src" -vf "scale='if(gt(iw,ih),-2,1080)':'if(gt(iw,ih),1080,-2)':flags=lanczos:$r,format=yuv420p" \
    -c:v libx264 -preset veryfast -crf 18 -c:a aac -b:a 192k -colorspace bt709 -color_primaries bt709 -color_trc bt709 \
    -movflags +faststart -f mp4 "$o.part" && mv "$o.part" "$o"
  [[ "$src" != "$f" ]] && mv "$src" ~/.Trash/ 2>/dev/null
  echo "wrote $o"
done
