# Jetson YOLO inference image (JetPack 6)
# Build (on the Jetson): docker build -t jetson-yolo -f deploy/Dockerfile deploy
ARG BASE_IMAGE=ultralytics/ultralytics:latest-jetson-jetpack6
FROM ${BASE_IMAGE}

# The pip OpenCV wheels are built without GStreamer, so nvarguscamerasrc (CSI camera) can't be opened.
# Replace them with Ubuntu's python3-opencv, which has GStreamer support.
RUN pip uninstall -y opencv-python opencv-python-headless opencv-contrib-python opencv-contrib-python-headless || true \
 && apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3-opencv \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir fastapi uvicorn \
 && python3 -c "import cv2, sys; sys.exit(0 if any('GStreamer' in l and 'YES' in l for l in cv2.getBuildInformation().splitlines()) else 'OpenCV has no GStreamer support')"

ENV PYTHONUNBUFFERED=1
WORKDIR /workspace
