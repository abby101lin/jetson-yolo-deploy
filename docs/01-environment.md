# 01 Jetson 系統環境確認

## 目標
確認 JetPack 版本、CUDA / TensorRT 已安裝，學會查看系統狀態，並依需求調整電源模式。

> 本文件的指令都在 **Jetson 上**執行。先在筆電的 PowerShell 輸入 `ssh jetson` 登入（見 [00](00-laptop-setup.md)），看到 `<帳號>@<主機名稱>:~$` 再開始。
> **一次只輸入一個指令**，等 `$` 再次出現後才輸入下一個。程式還在執行時就輸入，字會被那個程式吃掉，不會被當成新指令。

## 步驟

### 1.1 確認 JetPack / L4T 版本
```bash
cat /etc/nv_tegra_release
# 例：# R36 (release), REVISION: 5.0 → L4T 36.5 → JetPack 6.x
```
| L4T | JetPack | 備註 |
|---|---|---|
| R36.x | 6.x | 本專案目標版本（Ubuntu 22.04、Python 3.10） |
| R35.x | 5.x | 可用，但 PyTorch wheel / Docker image tag 需改用 JP5 版本 |

> 為什麼要確認版本：Docker 映像檔（`...-jetpack6`）、PyTorch wheel 都要配合 JetPack 的主版本選擇；JetPack 升級後，TensorRT engine 也要重新轉換。

### 1.2 確認 CUDA / TensorRT
JetPack 6 的系統映像檔通常已經內建 CUDA 和 TensorRT，**先確認，不一定要安裝**：
```bash
/usr/local/cuda/bin/nvcc --version                         # 最後一行：Build cuda_12.x...
python3 -c "import tensorrt; print(tensorrt.__version__)"  # 例：10.3.0
```

直接打 `nvcc` 出現 `command not found` 是正常的：nvcc 有裝，只是不在 PATH 裡。把它加進去，以後就能直接使用：
```bash
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc    # 附加到每次登入都會執行的設定檔
source ~/.bashrc                                             # 立刻生效
nvcc --version
```
> 要復原的話，刪掉 `~/.bashrc` 最後那一行就好。

**上面任一個找不到時**，再安裝 JetPack 的完整元件（會占用數 GB，包含範例程式和開發工具）：
```bash
sudo apt update
sudo apt install -y nvidia-jetpack python3-pip
```
> 採用 Docker 方案（[03](03-inference-env.md) 的做法 A）時，推論需要的東西都在容器裡，主機上**不一定**要裝 `nvidia-jetpack`。容器內的 TensorRT 版本可能和主機不同（例如容器是 10.7、主機是 10.3），這是正常的。

### 1.3 監控工具
```bash
which jtop || sudo pip3 install -U jetson-stats    # 沒有 jtop 才需要安裝（第一次安裝後要 sudo reboot）
sudo usermod -aG jtop $USER                         # 每個要用 jtop 的帳號都要加入 jtop 群組
exit                                                # 群組要重新登入才會生效，接著重新 ssh 登入
```
重新登入後：
```bash
id -nG     # 要看到 jtop
jtop       # 監控 GPU / CPU / 記憶體 / 溫度 / 功耗，按 q 離開
```
- 出現 `I can't access jtop.service. Please logout or reboot this board.`：代表帳號不在 jtop 群組，或加入後還沒重新登入。
- `usermod` 一定要用 `-aG`。少了 `-a`，帳號會被移出 sudo、docker、video 等其他群組。
- jtop 是全螢幕的文字介面，在 **VS Code 內建的終端機**裡可能會卡住。建議改用**獨立的 Windows PowerShell 視窗**，或是用比較輕量的 `tegrastats`：
  ```bash
  timeout 5 tegrastats      # 每秒印一行，5 秒後自動停止
  ```
  每一行的重點：`CPU [使用率%@時脈MHz,...]`、`GR3D_FREQ`（GPU 使用率，瞬間值，跳動是正常的）、`gpu@xxC`（溫度）、`VDD_IN`（整機功耗，mW）。
- 視窗太窄時，jtop 會省略 GPU、溫度等欄位，把視窗拉寬或按 `2` 切到 GPU 分頁就能看到。

### 1.4 電源模式
⚠️ **模式編號是看板子而定的，一定要先查再改。** 以 Orin Nano 8GB Super 為例，`-m 0` 是 **15W**（最省電），不是最高效能。

```bash
sudo nvpmodel -q                                # 查詢目前模式（第二行是編號）
grep "POWER_MODEL ID" /etc/nvpmodel.conf        # 列出這塊板子可用的模式
```
Orin Nano 8GB Super（JetPack 6.2 以上）的範例輸出：
```
< POWER_MODEL ID=0 NAME=15W >
< POWER_MODEL ID=1 NAME=25W >
< POWER_MODEL ID=2 NAME=MAXN_SUPER >
```
依照查到的編號切換，再確認一次：
```bash
sudo nvpmodel -m <編號>       # 例：上面的板子要 MAXN_SUPER 就是 -m 2
sudo nvpmodel -q
```
- 如果出現 `Reboot required`，代表要重新開機才會生效。
- **電源模式是「上限」，不是實際耗電量**。工作量沒超過目前模式的能力時，調高模式不會讓 FPS 變高，功耗也只會多一點點（實測：推論 30 FPS 時，25W 約 7.5W、MAXN_SUPER 約 7.9W）。等模型變大、FPS 跟不上時，再考慮調高。
- 重開機後，模式**不一定**會保留（實測曾被設回預設值）。開機後請用 `sudo nvpmodel -q` 確認。預設值可以用 `grep "PM_CONFIG DEFAULT" /etc/nvpmodel.conf` 查看。

鎖定最高時脈（選用）：
```bash
sudo jetson_clocks             # 鎖定最高時脈：更耗電、更熱，重開機後會失效
sudo jetson_clocks --restore   # 恢復
```

### 1.5 釋放記憶體（視需要）
Orin Nano 的 CPU 和 GPU **共用** 8GB 記憶體。先查看記憶體狀態，再決定需不需要調整：
```bash
free -h
```
| 看哪一欄 | 意思 |
|---|---|
| `Mem:` 那一行的 **available** | 真正還能用的量（free 加上可以釋放的快取）。**看這一欄就對了** |
| `Swap:` 那一行的 **used** | 已經用掉的備用 swap。0B 代表記憶體還很充裕 |

- **available 還有好幾 GB、Swap used 是 0** → 不需要調整
- **available 剩不到約 500MB、Swap used 持續增加、轉換 TensorRT 時當機** → 做下面的調整

JetPack 6 預設已經有 **zram swap**（壓縮過的記憶體交換區，約 3.7GB），可以用 `swapon --show` 查看。還是不夠時：
```bash
# 關閉桌面環境（GUI），可省下約 0.5～1GB
sudo systemctl set-default multi-user.target     # 要恢復就改成 graphical.target，再 sudo reboot
# 加上 8GB 的 swap 檔案
sudo fallocate -l 8G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```
> ⚠️ 關閉 GUI 後，Jetson 接上螢幕只會看到文字登入畫面，沒有桌面可以使用。只適合不接螢幕、只用 SSH 操作的（headless）部署。

## 關機
拔電源之前請先正常關機，避免正在寫入的檔案損壞：
```bash
sudo shutdown -h now
```
等板子的燈號熄滅、風扇停止後再拔電源。從 Jetson 的桌面關機時，如果出現 `other users are logged in`，那是還開著的 SSH 連線（通常就是你自己的），確認沒有其他人正在使用後就可以關機。設定和推論服務（Docker `--restart unless-stopped`）在開機後都會自動恢復。

## 驗證
```bash
bash scripts/check_env.sh
```

## 完成條件
- [ ] L4T R36.x
- [ ] `nvcc`、`tensorrt` 可用
- [ ] `jtop` 或 `tegrastats` 可以看到 GPU / 溫度 / 功耗
- [ ] 已經查過這塊板子的電源模式編號，並設為需要的模式（`sudo nvpmodel -q` 確認）
- [ ] `free -h` 的 available 足夠
