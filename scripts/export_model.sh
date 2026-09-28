#!/usr/bin/env bash
# Export models/best.pt to TensorRT engine (must run on the Jetson itself)
# Usage: bash scripts/export_model.sh [imgsz] [fp16|int8] [data.yaml for int8]
set -e
cd "$(dirname "$0")/../models"
IMGSZ=${1:-640}
PRECISION=${2:-fp16}

if [ "$PRECISION" = "int8" ]; then
  DATA=${3:?int8 requires data.yaml for calibration}
  yolo export model=best.pt format=engine int8=True data="$DATA" imgsz=$IMGSZ device=0
else
  yolo export model=best.pt format=engine half=True imgsz=$IMGSZ device=0
fi

ls -lh best.engine
