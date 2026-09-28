# 03 推論環境安裝

## 目標
讓 Ultralytics、PyTorch（CUDA）、支援 GStreamer 的 OpenCV 都能正常使用。

有兩種做法可以選：

| 做法 | 優點 | 缺點 |
|---|---|---|
| **A. Docker（推薦）** | 版本已經對齊好，環境可以重現 | 映像檔很大（數 GB），要額外掛載相機 socket |
| B. 原生安裝 | 除錯方便，不必多一層容器 | PyTorch / OpenCV 版本容易衝突 |

---

## A. Docker

### A.1 讓一般使用者可以執行 docker
```bash
sudo usermod -aG docker $USER      # 一定要用 -aG（少了 -a 會把使用者從其他群組移除）
# 重新登入後生效（或先執行 newgrp docker）
docker ps                          # 不加 sudo 也能執行，就是成功了
```

### A.2 建立專案映像檔
官方的 `ultralytics/ultralytics:latest-jetson-jetpack6` **不能直接使用**：
- 裡面的 OpenCV 是 pip 版的 `opencv-python-headless`，**不支援 GStreamer**，所以打不開 CSI 相機
- 沒有 fastapi / uvicorn

[deploy/Dockerfile](../deploy/Dockerfile) 以官方映像檔為基礎，改裝 Ubuntu 的 `python3-opencv`（支援 GStreamer），並補裝 fastapi / uvicorn。如果建完的 OpenCV 還是不支援 GStreamer，build 會直接失敗。
```bash
cd ~/jetson-yolo-deploy
docker build -t jetson-yolo -f deploy/Dockerfile deploy     # 第一次會下載基底映像檔（約 8GB，解壓縮後約 23GB）
```

### A.3 進入容器
```bash
docker run -it --rm --ipc=host --runtime=nvidia --network host \
  -v /tmp/argus_socket:/tmp/argus_socket \
  -v ~/jetson-yolo-deploy:/workspace \
  jetson-yolo
```
- `/tmp/argus_socket` 一定要掛載，否則容器內的 `nvarguscamerasrc` 會打不開相機。
- 容器內的 TensorRT 版本和 Jetson 本機不同（例如容器是 10.7、本機是 10.3），所以 **engine 一定要在容器內轉換，並在容器內執行**。

### A.4 驗證
在容器內執行：
```bash
python3 -c "import torch; print(torch.__version__, torch.cuda.is_available())"     # 要是 True
python3 -c "import cv2; print([l.strip() for l in cv2.getBuildInformation().splitlines() if 'GStreamer' in l])"   # 要是 YES
yolo predict model=models/best.pt source=test.jpg device=0                        # 模型可以正常載入並推論
```

## B. 原生安裝

### 3.1 PyTorch / torchvision
**不能**直接 `pip install torch`（PyPI 上的 aarch64 版本沒有 CUDA），要改裝 NVIDIA 為 Jetson 編譯的 wheel。
請依照 [Ultralytics NVIDIA Jetson 指南](https://docs.ultralytics.com/guides/nvidia-jetson/) 裡對應 JetPack 版本的指令安裝。

### 3.2 Ultralytics
```bash
pip3 install -U pip
pip3 install ultralytics
pip3 install -r app/requirements.txt
```

### 3.3 驗證 PyTorch 可以使用 CUDA
```bash
python3 -c "import torch; print(torch.__version__, torch.cuda.is_available())"
# 應該要印出 True
```
> 如果安裝 ultralytics 時把 torch 換成 PyPI 上的 CPU 版，要重新安裝一次 3.1 的 wheel。

---

## OpenCV GStreamer 檢查（兩種做法都必須做）

```bash
python3 -c "import cv2; print(cv2.__version__); print([l.strip() for l in cv2.getBuildInformation().splitlines() if 'GStreamer' in l])"
```
- 顯示 `GStreamer: YES` → OK
- 顯示 `NO` → pip 版的 opencv 蓋掉了系統版，要改回系統版：
```bash
pip3 uninstall -y opencv-python opencv-python-headless
sudo apt install -y python3-opencv
```

## 完成條件
- [ ] `torch.cuda.is_available()` 回傳 True
- [ ] OpenCV 顯示 GStreamer: YES
- [ ] 選用的做法：☐ Docker ☐ 原生
