# 02 MIPI CSI 相機啟用與測試

## 目標
讓 CSI 相機能透過 `nvarguscamerasrc`（Argus ISP 管線）正常取得影像。

> ⚠️ CSI 相機輸出的是 raw Bayer 資料，必須經過 Jetson ISP 處理。請使用 `nvarguscamerasrc`，**不要**用 `cv2.VideoCapture(0)` 直接開啟。

## 步驟

### 2.1 硬體連接
- **斷電**後再接排線。Orin Nano 開發板用的是 22-pin CSI 排線（和樹莓派的 15-pin 不同，可能需要轉接線）。
- 注意排線金屬接點的方向。

### 2.2 設定 CSI 接腳（第一次使用時需要做）
```bash
sudo /opt/nvidia/jetson-io/jetson-io.py
# → Configure Jetson 24pin CSI Connector
# → Configure for compatible hardware
# → 選擇相機型號（例：Camera IMX219 Dual / IMX477-A）
# → Save pin changes → Save and reboot to reconfigure pins
```

### 2.3 確認相機有被偵測到
```bash
ls /dev/video*                       # 應該看得到 /dev/video0
sudo apt install -y v4l-utils
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --list-formats-ext    # 查看支援的解析度和 FPS
```

### 2.4 拍照測試（遠端無螢幕）
```bash
bash scripts/test_camera.sh          # 產生 test.jpg
# 在開發機把照片拿回來看：
scp user@<jetson-ip>:~/jetson-yolo-deploy/test.jpg .
```

### 2.5 錄影測試（選做）
```bash
gst-launch-1.0 -e nvarguscamerasrc sensor-id=0 num-buffers=300 ! \
  'video/x-raw(memory:NVMM),width=1920,height=1080,framerate=30/1' ! \
  nvv4l2h264enc ! h264parse ! mp4mux ! filesink location=test.mp4
```

## 常用參數
| 參數 | 說明 |
|---|---|
| `sensor-id` | 相機編號（0 / 1，雙相機時使用） |
| `sensor-mode` | 指定感光元件模式（不同解析度 / FPS 組合） |
| `wbmode`、`exposuretimerange`、`gainrange` | 白平衡、曝光、增益 |

## 完成條件
- [ ] `/dev/video0` 存在
- [ ] `test.jpg` 畫面正常（沒有偏色，方向正確）
- [ ] 記錄使用的解析度 / FPS：`________`
