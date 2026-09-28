import os
import threading
import time
from pathlib import Path

import cv2
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = os.getenv("MODEL_PATH", str(BASE_DIR.parent / "models" / "best.engine"))
MODEL_TASK = os.getenv("MODEL_TASK", "detect")
SENSOR_ID = int(os.getenv("SENSOR_ID", "0"))
CAM_WIDTH = int(os.getenv("CAM_WIDTH", "1280"))
CAM_HEIGHT = int(os.getenv("CAM_HEIGHT", "720"))
CAM_FPS = int(os.getenv("CAM_FPS", "30"))
IMGSZ = int(os.getenv("IMGSZ", "640"))
CONF = float(os.getenv("CONF", "0.25"))
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", "80"))


def gst_pipeline(sensor_id, width, height, fps):
    return (
        f"nvarguscamerasrc sensor-id={sensor_id} ! "
        f"video/x-raw(memory:NVMM),width={width},height={height},framerate={fps}/1 ! "
        f"nvvidconv ! video/x-raw,format=BGRx ! videoconvert ! "
        f"video/x-raw,format=BGR ! appsink drop=1 max-buffers=1"
    )


model = YOLO(MODEL_PATH, task=MODEL_TASK)
cap = cv2.VideoCapture(gst_pipeline(SENSOR_ID, CAM_WIDTH, CAM_HEIGHT, CAM_FPS), cv2.CAP_GSTREAMER)
if not cap.isOpened():
    raise RuntimeError("Camera open failed: check nvargus-daemon and OpenCV GStreamer support")

lock = threading.Lock()
state = {"jpg": None, "detections": [], "timestamp": 0.0, "fps": 0.0}


def infer_loop():
    last = time.time()
    while True:
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.01)
            continue

        r = model(frame, imgsz=IMGSZ, conf=CONF, verbose=False)[0]
        dets = []
        if r.boxes is not None:
            dets = [
                {
                    "cls": model.names[int(b.cls)],
                    "conf": round(float(b.conf), 3),
                    "xyxy": [round(v, 1) for v in b.xyxy[0].tolist()],
                }
                for b in r.boxes
            ]
        _, jpg = cv2.imencode(".jpg", r.plot(), [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])

        now = time.time()
        with lock:
            state["jpg"] = jpg.tobytes()
            state["detections"] = dets
            state["timestamp"] = now
            state["fps"] = 0.9 * state["fps"] + 0.1 * (1.0 / max(now - last, 1e-6))
        last = now


threading.Thread(target=infer_loop, daemon=True).start()
app = FastAPI(title="Jetson YOLO Inference")


@app.get("/health")
def health():
    with lock:
        return {
            "model": MODEL_PATH,
            "fps": round(state["fps"], 1),
            "last_frame_age_s": round(time.time() - state["timestamp"], 2) if state["timestamp"] else None,
        }


@app.get("/detections")
def detections():
    with lock:
        return JSONResponse({"timestamp": state["timestamp"], "detections": state["detections"]})


@app.get("/stream")
def stream():
    def gen():
        while True:
            with lock:
                buf = state["jpg"]
            if buf:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf + b"\r\n"
            time.sleep(1.0 / CAM_FPS)

    return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")
