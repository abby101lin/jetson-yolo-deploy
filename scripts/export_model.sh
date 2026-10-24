#!/usr/bin/env bash
# Export a .pt in models/ to a TensorRT engine.
# Run INSIDE the jetson-yolo container (docs/03 A.3): the engine is tied to the TensorRT version it is built with.
# Usage: [MODEL=best_v2.pt] bash scripts/export_model.sh [imgsz] [fp16|int8] [data.yaml for int8]
set -e
cd "$(dirname "$0")/../models"
MODEL=${MODEL:-best.pt}
IMGSZ=${1:-640}
PRECISION=${2:-fp16}

command -v yolo >/dev/null || { echo "yolo not found: run this inside the jetson-yolo container (docs/03 A.3)" >&2; exit 1; }
[ -f "$MODEL" ] || { echo "models/$MODEL not found" >&2; exit 1; }

# TensorRT goes quiet for several minutes after "Compiler backend is used during engine build" — that is normal.
if [ "$PRECISION" = "int8" ]; then
  DATA=${3:?int8 requires data.yaml for calibration}
  yolo export model="$MODEL" format=engine int8=True data="$DATA" imgsz=$IMGSZ device=0
else
  yolo export model="$MODEL" format=engine quantize=16 imgsz=$IMGSZ device=0
fi

# The container runs as root; hand the outputs back to whoever owns models/ so they can be replaced later.
if [ "$(id -u)" = 0 ]; then
  chown --reference=. "${MODEL%.pt}".engine "${MODEL%.pt}".onnx 2>/dev/null || true
fi
ls -lh "${MODEL%.pt}".engine
