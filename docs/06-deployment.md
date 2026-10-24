# 06 開機自動啟動（systemd）

## 目標
讓推論服務在開機後自動啟動，異常結束時也會自動重新啟動。

## 步驟

### 6.1 修改服務檔
編輯 [deploy/yolo.service](../deploy/yolo.service)，把 `<USER>` 換成 Jetson 上的使用者名稱。

### 6.2 安裝並啟用
```bash
sudo cp deploy/yolo.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now yolo
```

### 6.3 管理指令
```bash
systemctl status yolo
journalctl -u yolo -f            # 即時 log
sudo systemctl restart yolo      # 更新模型或程式後要執行
sudo systemctl disable --now yolo
```

## 使用 Docker 時
改成用容器的 restart policy，就不需要 systemd 服務檔：
先依 [03-inference-env.md](03-inference-env.md) A.2 建好 `jetson-yolo` 映像檔，再執行：
```bash
docker run -d --name yolo --restart unless-stopped \
  --ipc=host --runtime=nvidia --network host \
  -v /tmp/argus_socket:/tmp/argus_socket \
  -v ~/jetson-yolo-deploy:/workspace -w /workspace/app \
  jetson-yolo \
  python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```
- 管理指令：`docker logs -f yolo`、`docker restart yolo`、`docker rm -f yolo`
- 更新流程的第 2、3 步改成在容器內 export，然後執行 `docker restart yolo`

## 更新流程
詳細步驟見 [04-model-export.md](04-model-export.md)。
1. 開發機：`scp models\best_v2.pt jetson:~/jetson-yolo-deploy/models/`（用新檔名，保留舊模型以便換回）
2. Jetson：進入 `jetson-yolo` 容器，執行 `MODEL=best_v2.pt bash scripts/export_model.sh`
3. Jetson：
   - systemd 原生部署：把 `deploy/yolo.service` 的 `MODEL_PATH` 改成新的 engine，再執行 `sudo systemctl daemon-reload && sudo systemctl restart yolo`
   - Docker 部署：`docker rm -f yolo`，用新的 `-e MODEL_PATH=...` 重新 `docker run`（見 04 的 4.6）
4. 確認 `/health` 顯示新的模型路徑，`/stream` 畫面正常

## 完成條件
- [ ] 重新開機後，服務自動啟動
- [ ] 手動 `kill` 程序後會自動重新啟動
