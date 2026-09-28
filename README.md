# Jetson Orin Nano YOLO 推論服務

把訓練好的 Ultralytics YOLO 模型（`best.pt`）部署到遠端 **Jetson Orin Nano**，透過 **MIPI CSI 相機**擷取影像，並以 TensorRT 加速推論，對外提供 HTTP 串流與 JSON API。

## 系統架構

```
[開發機] best.pt ──scp──▶ [Jetson Orin Nano] 轉 TensorRT engine
                                    │
   MIPI Camera ─▶ nvarguscamerasrc (GStreamer) ─▶ OpenCV ─▶ YOLO (best.engine)
                                                              │
                                      FastAPI：/stream (MJPEG)、/detections (JSON)、/health
```

## 前提假設

| 項目 | 假設 |
|---|---|
| 硬體 | Jetson Orin Nano (8GB) Developer Kit |
| 系統 | JetPack 6.x（L4T R36.x、Ubuntu 22.04、Python 3.10） |
| 相機 | IMX219 / IMX477 等 CSI 相機 |
| 模型 | Ultralytics YOLOv8 / YOLO11，`best.pt` |

## 專案結構

```
jetson-yolo-deploy/
├── README.md                  # 本文件
├── .githooks/pre-commit       # commit 前的隱私檢查（IP / 密碼 / 金鑰）
├── docs/                      # 部署流程文件（依序執行）
│   ├── 00-laptop-setup.md     # 開發機（筆電）環境初始化、SSH 金鑰
│   ├── 01-environment.md      # Jetson 系統環境確認與效能設定
│   ├── 02-camera.md           # MIPI 相機啟用與測試
│   ├── 03-inference-env.md    # 推論環境安裝（Docker / 原生）
│   ├── 04-model-export.md     # 上傳模型並轉換 TensorRT
│   ├── 05-inference-service.md# 推論服務說明與啟動
│   ├── 06-deployment.md       # systemd 開機自動啟動
│   └── 07-troubleshooting.md  # 常見問題排除
├── app/
│   ├── server.py              # FastAPI 推論服務
│   └── requirements.txt
├── deploy/
│   ├── Dockerfile             # 推論映像檔（OpenCV 改用支援 GStreamer 的版本）
│   └── yolo.service           # systemd 服務設定
├── scripts/
│   ├── check_env.sh           # 檢查 JetPack / CUDA / OpenCV GStreamer
│   ├── test_camera.sh         # 相機拍照測試
│   └── export_model.sh        # best.pt → best.engine
└── models/                    # 放置 best.pt / best.engine（不進版控）
```

## 快速開始

> 第一次使用請先依 [docs/00-laptop-setup.md](docs/00-laptop-setup.md) 設定好自己的筆電（git、隱私檢查、SSH 金鑰）。

```bash
# 1. 開發機：上傳專案與模型
scp -r jetson-yolo-deploy user@<jetson-ip>:~/
scp best.pt user@<jetson-ip>:~/jetson-yolo-deploy/models/

# 2. Jetson：依序執行
cd ~/jetson-yolo-deploy
bash scripts/check_env.sh          # 環境檢查
bash scripts/test_camera.sh        # 相機測試 → models/../test.jpg
bash scripts/export_model.sh       # 產生 models/best.engine
pip3 install -r app/requirements.txt
cd app && python3 -m uvicorn server:app --host 0.0.0.0 --port 8000

# 3. 瀏覽器
http://<jetson-ip>:8000/stream       # 即時畫面
http://<jetson-ip>:8000/detections   # 偵測結果 JSON
```

完整步驟請依序閱讀 [docs/](docs/)。

## 部署進度檢查表

- [ ] 00 筆電完成設定，`ssh jetson` 可以免密碼登入
- [ ] 01 確認 JetPack 版本、開啟 MAXN 效能模式
- [ ] 02 jetson-io 設定 CSI，相機拍照測試成功
- [ ] 03 PyTorch (CUDA) 可用、OpenCV 支援 GStreamer
- [ ] 04 在 Jetson 本機產生 `best.engine`
- [ ] 05 推論服務可從遠端瀏覽 `/stream`
- [ ] 06 systemd 開機自動啟動
- [ ] 記錄實測 FPS / 延遲 / 溫度（見 [05-inference-service.md](docs/05-inference-service.md)）
