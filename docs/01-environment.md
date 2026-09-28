# 01 Jetson 系統環境確認

## 目標
確認 JetPack 版本、CUDA / TensorRT 已安裝，並開啟最大效能模式。

## 步驟

### 1.1 確認 JetPack / L4T 版本
```bash
cat /etc/nv_tegra_release
# 例：# R36 (release), REVISION: 4.3 → JetPack 6.x
```
| L4T | JetPack | 備註 |
|---|---|---|
| R36.x | 6.x | 本專案目標版本（Ubuntu 22.04、Python 3.10） |
| R35.x | 5.x | 可用，但 PyTorch wheel / Docker image tag 需改用 JP5 版本 |

### 1.2 安裝 JetPack 元件（CUDA、cuDNN、TensorRT）
```bash
sudo apt update
sudo apt install -y nvidia-jetpack python3-pip
nvcc --version                                   # 如果找不到，把 /usr/local/cuda/bin 加進 PATH
python3 -c "import tensorrt; print(tensorrt.__version__)"
```

### 1.3 監控工具
```bash
sudo pip3 install -U jetson-stats
sudo reboot     # 第一次安裝後要重新開機
jtop            # 監控 GPU / CPU / 記憶體 / 溫度 / 功耗
```

### 1.4 效能模式
```bash
sudo nvpmodel -q          # 查詢目前模式
sudo nvpmodel -m 0        # MAXN（JetPack 6.2 以上是 MAXN SUPER）
sudo jetson_clocks        # 鎖定最高時脈（重新開機後會失效，可寫進 systemd）
```

### 1.5 釋放記憶體（建議）
Orin Nano 的 CPU 和 GPU 共用 8GB 記憶體，無頭（headless）部署時建議關掉桌面環境，並加上 swap：
```bash
sudo systemctl set-default multi-user.target     # 關閉 GUI（要恢復就改成 graphical.target）
sudo fallocate -l 8G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 驗證
```bash
bash scripts/check_env.sh
```

## 完成條件
- [ ] L4T R36.x
- [ ] `nvcc`、`tensorrt` 可用
- [ ] nvpmodel 設為模式 0
