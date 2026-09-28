#!/usr/bin/env bash
# Capture one frame from CSI camera to test.jpg
# Usage: bash scripts/test_camera.sh [sensor_id] [width] [height]
set -e
SENSOR_ID=${1:-0}
WIDTH=${2:-1920}
HEIGHT=${3:-1080}
OUT="$(dirname "$0")/../test.jpg"

gst-launch-1.0 -e nvarguscamerasrc sensor-id=$SENSOR_ID num-buffers=30 ! \
  "video/x-raw(memory:NVMM),width=$WIDTH,height=$HEIGHT" ! \
  nvvidconv ! nvjpegenc ! multifilesink location="$OUT" max-files=1

echo "Saved: $(realpath "$OUT")"
