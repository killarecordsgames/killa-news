#!/bin/bash
# Uso: anteprime.sh TAG.wav ORIGINALE.wav USCITA.mp3
# Mette il tag vocale a 4 s e poi ogni 30 s, MP3 192 kbps con dissolvenza finale.
set -e
TAG="$1"; IN="$2"; OUT="$3"
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$IN")
N=$(python3 -c "import math; print(int(($DUR-6)//30)+1)")
FILTER="[1:a]loudnorm=I=-14,volume=0.9,asplit=$N"
for i in $(seq 0 $((N-1))); do FILTER="$FILTER[t$i]"; done
FILTER="$FILTER;"
MIX="[0:a]"
for i in $(seq 0 $((N-1))); do
  MS=$(( (4 + i*30) * 1000 ))
  FILTER="$FILTER[t$i]adelay=${MS}|${MS}[d$i];"
  MIX="$MIX[d$i]"
done
FADE=$(python3 -c "print(max(0,$DUR-3))")
FILTER="$FILTER${MIX}amix=inputs=$((N+1)):normalize=0,alimiter=limit=0.89:level=false,afade=t=out:st=$FADE:d=3[out]"
ffmpeg -y -loglevel error -i "$IN" -i "$TAG" -filter_complex "$FILTER" -map "[out]" -ar 44100 -b:a 192k "$OUT"
