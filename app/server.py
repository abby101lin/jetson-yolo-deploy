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
AXES_STEP = int(os.getenv("AXES_STEP", "100"))  # pixel spacing of x/y axis ticks; 0 disables


def gst_pipeline(sensor_id, width, height, fps):
    return (
        f"nvarguscamerasrc sensor-id={sensor_id} ! "
        f"video/x-raw(memory:NVMM),width={width},height={height},framerate={fps}/1 ! "
        f"nvvidconv ! video/x-raw,format=BGRx ! videoconvert ! "
        f"video/x-raw,format=BGR ! appsink drop=1 max-buffers=1"
    )


def put_label(img, text, org, scale=0.45):
    # Black outline under white text so labels stay readable on any background.
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), 1, cv2.LINE_AA)


def draw_axes(img, step, dets):
    # Image coordinates, same as /detections xyxy: origin top-left, x to the right, y downward.
    h, w = img.shape[:2]
    grid = img.copy()
    for x in range(step, w, step):
        cv2.line(grid, (x, 0), (x, h), (255, 255, 255), 1)
    for y in range(step, h, step):
        cv2.line(grid, (0, y), (w, y), (255, 255, 255), 1)
    cv2.addWeighted(grid, 0.25, img, 0.75, 0, img)

    for x in range(step, w, step):
        cv2.line(img, (x, 0), (x, 8), (0, 255, 255), 2)
        put_label(img, str(x), (x - 12, 22))
    for y in range(step, h, step):
        cv2.line(img, (0, y), (8, y), (0, 255, 255), 2)
        put_label(img, str(y), (12, y + 5))
    put_label(img, "0", (4, 16))
    # Axis arrows sit inside the tick rows so they don't cover the last tick labels.
    cv2.arrowedLine(img, (w - 70, 40), (w - 15, 40), (0, 255, 255), 2, tipLength=0.3)
    put_label(img, "x", (w - 88, 46), 0.6)
    cv2.arrowedLine(img, (60, h - 70), (60, h - 15), (0, 255, 255), 2, tipLength=0.3)
    put_label(img, "y", (68, h - 40), 0.6)

    for d in dets:
        x1, y1, x2, y2 = d["xyxy"]
        cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
        cv2.circle(img, (cx, cy), 4, (0, 0, 255), -1)
        put_label(img, f"({cx},{cy})", (cx + 6, cy - 6))


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
        annotated = r.plot()
        if AXES_STEP > 0:
            draw_axes(annotated, AXES_STEP, dets)
        _, jpg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])

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
