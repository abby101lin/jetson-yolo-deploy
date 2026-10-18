#!/usr/bin/env bash
# Capture one frame from CSI camera to test.jpg
# Usage: bash scripts/test_camera.sh [sensor_id] [width] [height]
# The CSI camera serves one client at a time: stop the inference service first (docker stop yolo).
SENSOR_ID=${1:-0}
WIDTH=${2:-1920}
HEIGHT=${3:-1080}
OUT="$(dirname "$0")/../test.jpg"

rm -f "$OUT"
# gst-launch's exit code is unreliable here: a good capture can exit 1 (Argus prints CANCELLED
# on teardown) and a failed one can exit 0, so judge success by whether the file was written.
gst-launch-1.0 -e nvarguscamerasrc sensor-id=$SENSOR_ID num-buffers=30 ! \
  "video/x-raw(memory:NVMM),width=$WIDTH,height=$HEIGHT" ! \
  nvvidconv ! nvjpegenc ! multifilesink location="$OUT" max-files=1

if [ -s "$OUT" ]; then
  echo "Saved: $(realpath "$OUT")"
else
  echo "Capture failed: no image written." >&2
  echo "- Is another program using the camera? (docker ps; docker stop yolo, wait a few seconds, retry)" >&2
  echo "- Camera daemon stuck? (sudo systemctl restart nvargus-daemon)" >&2
  exit 1
fi
