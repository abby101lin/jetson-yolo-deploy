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

```bash
# 讓一般使用者可以執行 docker
sudo usermod -aG docker $USER && newgrp docker

sudo docker pull ultralytics/ultralytics:latest-jetson-jetpack6

sudo docker run -it --rm --ipc=host --runtime=nvidia --network host \
  -v /tmp/argus_socket:/tmp/argus_socket \
  -v ~/jetson-yolo-deploy:/workspace \
  -w /workspace \
  ultralytics/ultralytics:latest-jetson-jetpack6
```
- `/tmp/argus_socket` 一定要掛載，否則容器內的 `nvarguscamerasrc` 會打不開相機。
- 進到容器後，同樣要執行下方的「OpenCV GStreamer 檢查」。

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
