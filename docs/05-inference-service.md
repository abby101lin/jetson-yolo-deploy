# 05 推論服務

## 目標
執行 [app/server.py](../app/server.py)，持續從相機擷取影像並推論，讓遠端可以透過 HTTP 查看。

## 架構

```
推論執行緒（背景）：
  cap.read() → model() → 保存最新的偵測結果 + 標註後的 JPEG
                                  │（lock 保護）
FastAPI：
  GET /stream      → MJPEG 串流（multipart/x-mixed-replace）
  GET /detections  → 最新一幀的偵測結果 JSON
  GET /health      → 服務狀態 / FPS
```

- GStreamer 的 `appsink drop=1 max-buffers=1` 只保留最新一幀，避免延遲越積越多。
- 推論和 HTTP 串流分開執行，所以多位使用者同時觀看也不會拖慢推論速度。

## 設定（環境變數）

| 變數 | 預設值 | 說明 |
|---|---|---|
| `MODEL_PATH` | `../models/best.engine` | 模型路徑（也可以指定 .pt） |
| `MODEL_TASK` | `detect` | `detect` / `segment` / `pose` / `obb` / `classify` |
| `SENSOR_ID` | `0` | CSI 相機編號 |
| `CAM_WIDTH` / `CAM_HEIGHT` / `CAM_FPS` | `1280` / `720` / `30` | 相機擷取設定 |
| `IMGSZ` | `640` | 推論尺寸（要和 export 時一致） |
| `CONF` | `0.25` | 信心分數門檻 |
| `JPEG_QUALITY` | `80` | 串流畫質 |
| `AXES_STEP` | `100` | 在 `/stream` 畫面畫 XY 軸刻度和格線的間距（像素），並標出每個框的中心座標；`0` 不畫 |

## 啟動

```bash
cd ~/jetson-yolo-deploy/app
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```

## 測試
```bash
curl http://<jetson-ip>:8000/health
curl http://<jetson-ip>:8000/detections
# 瀏覽器打開 http://<jetson-ip>:8000/stream
```

`/detections` 回傳格式：
```json
{
  "timestamp": 1727500000.123,
  "detections": [
    {"cls": "person", "conf": 0.91, "xyxy": [102.3, 55.0, 380.1, 700.4]}
  ]
}
```

`/stream` 畫面上的 XY 軸和 `xyxy` 用同一套影像座標：原點 (0, 0) 在左上角，x 往右、y 往下，單位是像素（範圍是 `CAM_WIDTH` × `CAM_HEIGHT`）。每個框中心的紅點旁會標出 `(x, y)`，方便對照 JSON 的數值。

## 遠端存取安全
不要把 port 8000 直接開到公網。建議改用以下任一種方式：
- SSH tunnel：`ssh -L 8000:localhost:8000 user@<jetson-ip>`，然後在本機瀏覽 `http://localhost:8000/stream`
- VPN / Tailscale

## 效能調校
| 做法 | 效果 |
|---|---|
| 使用 FP16 / INT8 engine | 推論速度大幅提升 |
| 把 `IMGSZ` 降到 480 / 320 | 較快，但小物件可能漏偵測（需要重新 export） |
| 降低 `CAM_WIDTH/HEIGHT` | 減少前處理和 JPEG 編碼的負擔 |
| 不需要畫面時不呼叫 `r.plot()` | 節省 CPU（只提供 JSON） |

## 實測紀錄

| 日期 | 模型 | 相機解析度 | FPS | GPU 使用率 | 溫度 | 備註 |
|---|---|---|---|---|---|---|
| 2026-10-29 | `final.engine`（FP16，imgsz 640） | 1280×720 | 23～26 | — | — | 偵測氣球；開啟 XY 軸繪製後約 23 FPS |

## 完成條件
- [ ] 遠端可以看到 `/stream` 畫面，而且框的位置正確
- [ ] `/health` 的 FPS 達到需求：`____`
