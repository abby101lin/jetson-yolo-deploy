# 04 模型上傳與 TensorRT 轉換

## 目標
把 `.pt` 模型轉成 TensorRT engine（`.engine`），取得最佳推論效能，並讓推論服務改用新模型。

> ⚠️ engine 檔綁定 **GPU 型號和 TensorRT 版本**，一定要在 **Orin Nano 上**轉換，不能在開發機轉好再拷貝過來。
> 採用 Docker 方案時，容器內的 TensorRT 版本和 Jetson 主機不同（例如容器是 10.7、主機是 10.3），所以要**在 `jetson-yolo` 容器內轉換，也在容器內執行**。JetPack 升級或映像檔重新建立後，都要重新轉換。

## 步驟

### 4.1 上傳模型（在開發機執行）
1. 把模型放進筆電專案的 `models\` 資料夾，並**取一個新名字**（例：`best_v2.pt`），避免蓋掉正在使用的模型、之後也能換回來。
   > ⚠️ 一定要放在 `models\` 裡。放在專案根目錄的話，`.gitignore` 不會排除它，可能被推上公開的 GitHub（VS Code 會在檔名旁邊顯示綠色的 `U`）。
2. 在筆電的 PowerShell 傳到 Jetson（`jetson` 是 [00](00-laptop-setup.md) 設定的 SSH 別名）：
   ```powershell
   scp models\best_v2.pt jetson:~/jetson-yolo-deploy/models/
   ```
   規則是 `scp 來源 目的地`，有 `jetson:` 的那一邊就是 Jetson。

### 4.2 進入容器，先用 .pt 驗證
依 [03](03-inference-env.md) A.3 進入容器（提示字元變成 `root@<主機名稱>:/workspace#`），然後：
```bash
yolo predict model=models/best_v2.pt source=test.jpg device=0 project=runs
```
- 確認模型能載入、能在 GPU 上推論（輸出有 `CUDA:0`）。
- 加上 `project=runs`，標好框的圖片會存到專案的 `runs/` 資料夾（已被 `.gitignore` 排除）。沒加的話會存在容器裡，離開容器（`--rm`）後就消失了。
- 想知道模型偵測哪些類別、訓練時的尺寸：
  ```bash
  python3 -c "from ultralytics import YOLO; m=YOLO('models/best_v2.pt'); print(m.names, m.ckpt['train_args']['imgsz'])"
  ```

### 4.3 轉換為 TensorRT（在容器內，約 8 分鐘）
```bash
MODEL=best_v2.pt bash scripts/export_model.sh        # 預設：FP16、imgsz=640；產生 models/best_v2.engine
# 不指定 MODEL 就是轉換 best.pt
```
- 畫面出現 `Compiler backend is used during engine build.` 之後，會有**好幾分鐘沒有任何輸出**，這是 TensorRT 在測試最快的計算方式，**不要中斷**。看到 `export success ✅` 才是完成。
- 腳本會先產生 `.onnx`，再產生 `.engine`，並把檔案擁有者改回 `models/` 資料夾的擁有者（容器內是 root 身分，不改的話一般使用者之後無法覆蓋這些檔案）。
- `imgsz` 要和訓練時一致（或者是推論時打算使用的尺寸）。記憶體不足時，請參考 [01](01-environment.md) 1.5。
- 手動執行的寫法：
  ```bash
  yolo export model=models/best_v2.pt format=engine quantize=16 imgsz=640 device=0
  chown 1001:1002 models/best_v2.engine models/best_v2.onnx   # 數字換成你的 uid:gid（在 Jetson 上執行 id 查詢）
  ```

### 4.4 精度選項

| 選項 | 指令參數 | 速度 | 精度 |
|---|---|---|---|
| FP32 | （預設） | 基準 | 最高 |
| **FP16（推薦）** | `quantize=16`（舊版 Ultralytics 用 `half=True`） | 約 2～3 倍 | 幾乎沒有損失 |
| INT8 | `int8=True data=data.yaml` | 最快 | 會有少許損失，需要校正資料集 |

> Ultralytics 8.4 以後使用 `half=True` 會出現 `'half' is deprecated ... Use 'quantize' instead` 的警告，目前還能用，但之後會被移除。
> Orin Nano 沒有 DLA（Orin NX / AGX 才有），所以不需要設定 `dla` 參數。

### 4.5 驗證 engine（在容器內）
```bash
yolo predict model=models/best_v2.engine source=test.jpg device=0 project=runs
yolo val model=models/best_v2.engine data=data.yaml    # 如果有驗證集，可以比較 mAP
```
- 偵測結果應該和 .pt 一致。engine 的輸入尺寸固定（例如 `640x640`），.pt 會依照片比例調整（例如 `384x640`），這是正常的差異。
- 比較 `Speed:` 那一行的 **inference** 時間。單張照片的 preprocess / postprocess 包含第一次執行的準備時間，看起來會比較久；推論服務連續處理影像時就不會。

### 4.6 讓推論服務改用新模型
推論服務用環境變數 `MODEL_PATH` 決定載入哪個模型（見 [05](05-inference-service.md)）。容器的設定建立後就不能修改，所以要**刪掉舊容器，再用新設定重新建立**（刪掉容器不會刪掉映像檔、模型或程式）。先 `exit` 離開容器，在 Jetson 上執行：
```bash
docker rm -f yolo
docker run -d --name yolo --restart unless-stopped \
  --ipc=host --runtime=nvidia --network host \
  -v /tmp/argus_socket:/tmp/argus_socket \
  -v ~/jetson-yolo-deploy:/workspace -w /workspace/app \
  -e MODEL_PATH=/workspace/models/best_v2.engine \
  jetson-yolo python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
curl localhost:8000/health      # 剛啟動時 fps 是 0，等 10～20 秒後應該約 30，model 要是新的路徑
```
- 不希望開機自動啟動，就拿掉 `--restart unless-stopped`。之後可以用 `docker update --restart unless-stopped yolo`（或 `no`）調整。
- **換回舊模型**：同樣 `docker rm -f yolo`，把 `MODEL_PATH` 改回舊的 engine 再執行一次。所以舊的 `.pt` / `.engine` 請保留。
- 如果新模型用的是**同一個檔名**（覆蓋了 `best.engine`），就不用重新建立容器，`docker restart yolo` 即可。
- 實際用瀏覽器看即時畫面，確認框的位置和信心分數（見 [05](05-inference-service.md) 的 SSH tunnel）。誤判的分數很高時，調高 `CONF` 也解決不了，要回到訓練資料加入容易誤判的「非目標」照片（不標框）。

## 結果紀錄

| 模型 | imgsz | 精度 | 推論時間 (ms) | mAP50-95 | 備註 |
|---|---|---|---|---|---|
| best_v2.pt | 640 | FP32 | 29.7 | | 單張照片，`yolo predict` |
| best_v2.engine | 640 | FP16 | 11.2 | | 同上，約快 2.6 倍；服務約 30 FPS（受限於相機） |
| | | INT8 | | | |

## 完成條件
- [ ] `models/<模型名稱>.engine` 已產生，擁有者是一般使用者（不是 root）
- [ ] engine 的推論結果和 .pt 一致
- [ ] 推論服務的 `/health` 顯示新的模型路徑，fps 正常
