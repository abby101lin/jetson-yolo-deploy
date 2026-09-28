# 04 模型上傳與 TensorRT 轉換

## 目標
把 `best.pt` 轉成 TensorRT engine（`best.engine`），取得最佳推論效能。

> ⚠️ engine 檔綁定 **GPU 型號和 TensorRT 版本**，一定要在 **Orin Nano 本機**上轉換，不能在開發機轉好再拷貝過來。JetPack 升級後也要重新轉。

## 步驟

### 4.1 上傳模型（在開發機執行）
```bash
scp best.pt user@<jetson-ip>:~/jetson-yolo-deploy/models/
```

### 4.2 先用 .pt 做一次驗證（確認模型本身沒問題）
```bash
cd ~/jetson-yolo-deploy
yolo predict model=models/best.pt source=test.jpg save=True
# 結果會存在 runs/detect/predict/
```

### 4.3 轉換為 TensorRT
```bash
bash scripts/export_model.sh                 # 預設：FP16、imgsz=640
# 或手動執行：
yolo export model=models/best.pt format=engine half=True imgsz=640 device=0
```
- 轉換需要好幾分鐘，記憶體不足時請先加 swap（見 [01-environment.md](01-environment.md)）。
- `imgsz` 要和訓練時一致（或者是推論時打算使用的尺寸）。

### 4.4 精度選項

| 選項 | 指令參數 | 速度 | 精度 |
|---|---|---|---|
| FP32 | （預設） | 基準 | 最高 |
| **FP16（推薦）** | `half=True` | 約 2～3 倍 | 幾乎沒有損失 |
| INT8 | `int8=True data=data.yaml` | 最快 | 會有少許損失，需要校正資料集 |

> Orin Nano 沒有 DLA（Orin NX / AGX 才有），所以不需要設定 `dla` 參數。

### 4.5 驗證 engine
```bash
yolo predict model=models/best.engine source=test.jpg save=True
yolo val model=models/best.engine data=data.yaml    # 如果有驗證集，可以比較 mAP
```

## 結果紀錄

| 模型 | imgsz | 精度 | 推論時間 (ms) | mAP50-95 |
|---|---|---|---|---|
| best.pt | 640 | FP32 | | |
| best.engine | 640 | FP16 | | |
| best.engine | 640 | INT8 | | |

## 完成條件
- [ ] `models/best.engine` 已產生
- [ ] engine 的推論結果和 .pt 一致
