# 07 常見問題排除

## 相機

| 症狀 | 可能原因 | 處理方式 |
|---|---|---|
| 沒有 `/dev/video0` | 排線方向錯誤、沒有設定 jetson-io | 斷電後重新插排線，再執行 jetson-io 並重新開機 |
| `Failed to create CaptureSession` | argus daemon 卡住，或相機被其他程序占用 | `sudo systemctl restart nvargus-daemon`，並停止其他使用相機的程序 |
| 容器內打不開相機 | 沒有掛載 argus socket | 加上 `-v /tmp/argus_socket:/tmp/argus_socket` |
| 畫面偏紅或偏綠 | ISP 調校檔不符 | 確認相機型號和 jetson-io 的選項一致 |
| 畫面上下顛倒 | 相機安裝方向 | 在 pipeline 的 `nvvidconv` 加上 `flip-method=2` |

## 推論環境

| 症狀 | 處理方式 |
|---|---|
| `torch.cuda.is_available()` 是 False | torch 被換成 PyPI 上的 CPU 版，要重新安裝 Jetson wheel（見 03） |
| `cv2.VideoCapture` 回傳 False | OpenCV 沒有 GStreamer 支援（見 03 的檢查步驟），或 pipeline 字串有誤，可以先用 `gst-launch-1.0` 驗證 |
| `numpy` 版本衝突 | JetPack 6 的系統 OpenCV 需要 numpy<2：`pip3 install "numpy<2"` |

## 模型轉換 / 推論

| 症狀 | 處理方式 |
|---|---|
| export 時 OOM 或被 killed | 加 swap、關閉 GUI、停止其他服務 |
| 載入 engine 時出現版本錯誤 | engine 是在其他機器或其他 TRT 版本上轉的，要在本機重新 export |
| FPS 太低 | 確認使用的是 `.engine` 而不是 `.pt`、nvpmodel 設為模式 0，並執行 jetson_clocks；再降低 imgsz 或相機解析度 |
| 溫度過高、降頻 | 加強散熱（風扇 / 散熱片），用 `jtop` 觀察 |

## 除錯常用指令
```bash
jtop                                   # 資源監控
journalctl -u yolo -f                  # 服務 log
journalctl -u nvargus-daemon -f        # 相機 daemon log
GST_DEBUG=3 python3 server.py          # 顯示 GStreamer 詳細訊息
```

## 進階方向
- **RTSP 輸出**（接 NVR / VMS）：用 `nvv4l2h264enc` 硬體編碼，搭配 gst-rtsp-server
- **多路相機 / 量產**：改用 NVIDIA DeepStream
- **結果上拋**：把 `/detections` 改為 MQTT / WebSocket 主動推送
