# 02 MIPI CSI 相機啟用與測試

## 目標
讓 CSI 相機能透過 `nvarguscamerasrc`（Argus ISP 管線）正常取得影像。

> ⚠️ CSI 相機輸出的是 raw Bayer 資料，必須經過 Jetson ISP 處理。請使用 `nvarguscamerasrc`，**不要**用 `cv2.VideoCapture(0)` 直接開啟。

> ⚠️ **CSI 相機同一時間只能給一個程式使用。** 推論服務（[05](05-inference-service.md) / [06](06-deployment.md) 的 `yolo` 容器）在執行時會一直占用相機，這時拍照、錄影都會失敗。請先暫停服務，用完再啟動回來（見 2.4）。

## 步驟

### 2.1 硬體連接
- **斷電**後再接排線。Orin Nano 開發板用的是 22-pin CSI 排線（和樹莓派的 15-pin 不同，可能需要轉接線）。
- 注意排線金屬接點的方向。

### 2.2 設定 CSI 接腳（第一次使用時需要做）
> 先做 2.3。如果已經看得到 `/dev/video0` 和相機型號，代表接腳已經設定好了，**跳過這一步**。

```bash
sudo /opt/nvidia/jetson-io/jetson-io.py
# → Configure Jetson 24pin CSI Connector
# → Configure for compatible hardware
# → 選擇相機型號（例：Camera IMX219 Dual / IMX477-A）
# → Save pin changes → Save and reboot to reconfigure pins
```
> 存檔後會**重新開機**。選錯相機型號，相機會無法使用。

### 2.3 確認相機有被偵測到
```bash
ls /dev/video*                       # 應該看得到 /dev/video0
sudo apt install -y v4l-utils        # 已經安裝過就不用
v4l2-ctl --list-devices              # 會看到相機型號，例：imx219
v4l2-ctl -d /dev/video0 --list-formats-ext    # 查看支援的解析度和 FPS
```
`--list-formats-ext` 的輸出怎麼看（以 IMX219 為例）：
- `'RG10' (10-bit Bayer ...)`：相機輸出原始 Bayer 資料，要經過 ISP 轉換（所以要用 `nvarguscamerasrc`）
- 每一組 `Size` / `fps` 是一種解析度和最高 FPS 的組合。解析度越高，FPS 越低：

| 解析度 | 最高 FPS |
|---|---|
| 3280×2464 | 21 |
| 3280×1848 | 28 |
| 1920×1080 | 30 |
| 1640×1232 | 30 |
| 1280×720 | 60 |

### 2.4 拍照測試（遠端無螢幕）
在 Jetson 上，**一次執行一行**：
```bash
docker stop yolo                     # 1. 暫停推論服務，讓出相機（沒有在跑服務就跳過）
                                     #    執行完請等 3～5 秒，讓相機服務釋放完畢
cd ~/jetson-yolo-deploy
bash scripts/test_camera.sh          # 2. 拍照，最後一行顯示 Saved: .../test.jpg 就是成功
docker start yolo                    # 3. ⚠️ 一定要啟動回來
```
- 結束時出現幾行 `ERROR: ... CANCELLED` 是**正常的**。那是關閉相機時，正在進行的拍攝被取消；看到 `Done Success` 和 `Saved:` 就代表成功。
- 第 3 步不能省略。用 `docker stop` 停止的容器，Docker 會當成是**刻意停止的**，之後重開機也**不會**自動啟動。
- 拍照失敗、腳本顯示 `Capture failed` 時：
  1. 用 `docker ps` 確認推論服務已經停止，等幾秒再試一次
  2. 還是失敗，就重新啟動相機服務：`sudo systemctl restart nvargus-daemon`，然後再試
  3. 推論服務啟動後，`/health` 的 fps 一直是 0、log 出現 `Failed to create CaptureSession`，也一樣先重新啟動相機服務，再執行 `docker restart yolo`

在**筆電**的 PowerShell 把照片拿回來看（先在 Jetson 輸入 `exit` 回到 `PS ...>`）：
```powershell
scp jetson:~/jetson-yolo-deploy/test.jpg .     # jetson 是 00 設定的 SSH 別名
start test.jpg
```
確認顏色正常（沒有整張偏紅、偏綠）、方向正確、畫面清楚。

> `test.jpg`、`test.mp4` 可能拍到家裡或公司內部的畫面，已經被 `.gitignore` 排除，不會進版控。

### 2.5 錄影測試（選做）
**Orin Nano 沒有硬體影片編碼器**（Orin NX / AGX Orin 才有），所以 NVIDIA 範例常見的 `nvv4l2h264enc` 不能用，執行會出現：
```
WARNING: erroneous pipeline: no element "nvv4l2h264enc"
```
請改用 CPU 的軟體編碼器 `x264enc`。和 2.4 一樣，先 `docker stop yolo` 並等幾秒：
```bash
gst-launch-1.0 -e nvarguscamerasrc sensor-id=0 num-buffers=300 ! \
  'video/x-raw(memory:NVMM),width=1920,height=1080,framerate=30/1' ! \
  nvvidconv ! 'video/x-raw,format=I420' ! \
  x264enc speed-preset=ultrafast bitrate=8000 ! mp4mux ! filesink location=test.mp4
```
- `num-buffers=300`：錄 300 張畫面，30 FPS 就是 10 秒
- `nvvidconv ! 'video/x-raw,format=I420'`：把畫面從 GPU 記憶體（NVMM）轉到一般記憶體，CPU 編碼器才讀得到
- `speed-preset=ultrafast`：讓 CPU 跟得上 30 FPS；`bitrate=8000`：8 Mbps
- 錄完記得 `docker start yolo`；在筆電用 `scp jetson:~/jetson-yolo-deploy/test.mp4 .` 取回，再用 `start test.mp4` 播放

> 看懂 GStreamer 的錯誤：先找**被雙引號括起來的元件名稱**。GStreamer 一次只會回報**第一個**找不到的元件（上面的管線中，`h264parse` 其實也沒有安裝），修好一個，下一個才會出現。可以用 `gst-inspect-1.0 <元件名稱>` 確認某個元件是否存在。

## 常用參數
| 參數 | 說明 |
|---|---|
| `sensor-id` | 相機編號（0 / 1，雙相機時使用） |
| `sensor-mode` | 指定感光元件模式（不同解析度 / FPS 組合） |
| `wbmode`、`exposuretimerange`、`gainrange` | 白平衡、曝光、增益 |

## 完成條件
- [ ] `/dev/video0` 存在，`v4l2-ctl --list-devices` 看得到相機型號
- [ ] `test.jpg` 畫面正常（沒有偏色，方向正確）
- [ ] 拍完照後，推論服務已經 `docker start yolo` 恢復
- [ ] 記錄使用的解析度 / FPS：`________`
