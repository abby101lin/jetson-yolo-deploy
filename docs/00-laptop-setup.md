# 00 開發機（筆電）環境初始化

## 目標
在自己的筆電上完成下列設定，之後就能開發、推送程式碼，並且免密碼 SSH 連到 Jetson：
- 安裝 Git、VS Code（GitHub CLI 可選）
- 設定 git 作者，並用 noreply email 保護真實 email
- clone 專案，啟用隱私檢查 hook
- 建立**個人專用**的 SSH 金鑰，設定免密碼登入 Jetson

> 以下以 **Windows 10/11** 為主。macOS / Linux 的差異會另外標註。
> 文件中的 `<jetson-ip>`、`<你的帳號>`、`<名字>` 都是佔位符，請換成自己的值，但**不要**把真實值寫回專案檔案（見 [0.8 隱私規則](#08-隱私規則)）。

---

## 步驟

### 0.1 安裝工具
| 工具 | 用途 | 安裝 |
|---|---|---|
| Git | 版控；Windows 版內建 Git Bash 和 OpenSSH | https://git-scm.com/download/win |
| VS Code | 編輯器 | https://code.visualstudio.com/ |
| GitHub CLI（可選） | 登入 GitHub、建立 PR | https://cli.github.com/ |

Windows 可以用 winget 一次裝好：
```powershell
winget install --id Git.Git -e
winget install --id Microsoft.VisualStudioCode -e
winget install --id GitHub.cli -e      # 可選
```
> macOS：`brew install git gh`，並安裝 VS Code。Linux：`sudo apt install -y git openssh-client`。

裝好後，**重新開啟**終端機並確認：
```powershell
git --version
ssh -V
```

### 0.2 登入 GitHub
```powershell
gh auth login        # 選 GitHub.com → HTTPS → Login with a web browser
gh auth status       # 應該會顯示 Logged in to github.com account <你的帳號>
```
> 沒裝 gh 也可以。第一次 `git push` 時，Git Credential Manager 會跳出瀏覽器讓你登入。

### 0.3 設定 git 作者（使用 noreply email）
這是公開 repo，commit 的作者 email 任何人都看得到。建議改用 GitHub 提供的 noreply 地址：

1. GitHub → Settings → Emails → 勾選 **Keep my email addresses private**
2. 複製頁面上顯示的地址，格式是 `<數字>+<你的帳號>@users.noreply.github.com`
   （有裝 gh 的話，也可以直接查：`gh api user --jq '"\(.id)+\(.login)@users.noreply.github.com"'`）

```powershell
git config --global user.name  "<你的帳號>"
git config --global user.email "<數字>+<你的帳號>@users.noreply.github.com"
```
> 只想套用在這個專案，就在 clone 後進入專案資料夾，把上面兩行的 `--global` 拿掉再執行。

### 0.4 取得專案並啟用隱私檢查
```powershell
git clone https://github.com/abby101lin/jetson-yolo-deploy.git
cd jetson-yolo-deploy
git config core.hooksPath .githooks     # 每個人 clone 後都要執行一次
```
啟用後，每次 `git commit` 都會自動掃描這次新增的內容。發現下列資訊就會中止 commit，並列出是哪一行：
- 真實 IP（`0.0.0.0`、`127.x.x.x` 除外）
- `password=`、`token=`、`api_key=` 這類賦值
- 私鑰、GitHub token

確認一下：
```powershell
git config core.hooksPath      # 應該顯示 .githooks
```

### 0.5 建立個人專用 SSH 金鑰
**每個人各自建立一把**，不要共用別人的金鑰，這樣之後要撤銷某個人的權限也比較方便。檔名請帶上自己的名字：
```powershell
ssh-keygen -t ed25519 -C "<名字>@jetson-yolo-deploy" -f "$env:USERPROFILE\.ssh\id_ed25519_<名字>"
```
- 詢問 passphrase 時：直接按 Enter 就是不設密碼（方便自動化）；有輸入就是每次使用金鑰都要輸入（比較安全）。
- 會產生兩個檔案：
  - `id_ed25519_<名字>`：**私鑰**，只留在自己的筆電，絕對不要傳給別人或放進專案
  - `id_ed25519_<名字>.pub`：**公鑰**，要放到 Jetson 上

> macOS / Linux：路徑改成 `~/.ssh/id_ed25519_<名字>`。

### 0.6 把公鑰放到 Jetson
先確認 Jetson 上已經有你的帳號（沒有的話請找 Jetson 管理者，見 [Jetson 管理者：新增使用者](#jetson-管理者新增使用者)）。

**Windows（PowerShell）**：Windows 沒有 `ssh-copy-id`，所以改用下面這行。執行時會要你輸入**一次** Jetson 的密碼：
```powershell
type "$env:USERPROFILE\.ssh\id_ed25519_<名字>.pub" | ssh <你的帳號>@<jetson-ip> "mkdir -p ~/.ssh && chmod 700 ~/.ssh && tr -d '\r' | sed '1s/^\xEF\xBB\xBF//' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```
> 指令中的 `tr` / `sed` 不能省略。Windows PowerShell 5.1 在管線傳給 ssh 時，會在開頭加上 BOM，並把換行改成 CRLF。沒清掉的話，公鑰那一行會失效。
**macOS / Linux**：
```bash
ssh-copy-id -i ~/.ssh/id_ed25519_<名字>.pub <你的帳號>@<jetson-ip>
```

### 0.7 設定 SSH 連線別名
公鑰放好之後，直接打 `ssh <你的帳號>@<jetson-ip>` **還是會問密碼**，因為金鑰檔名不是預設的 `id_ed25519`，ssh 不會自動使用它。所以要在 `~/.ssh/config` 指定金鑰。

用 VS Code 開啟（檔案不存在時會自動建立）：
```powershell
code "$env:USERPROFILE\.ssh\config"
```
在檔案最後面加上：
```
Host jetson <jetson-ip>
  HostName <jetson-ip>
  User <你的帳號>
  IdentityFile ~/.ssh/id_ed25519_<名字>
  IdentitiesOnly yes
```
- `Host jetson <jetson-ip>`：打 `ssh jetson` 或 `ssh <jetson-ip>` 都會套用這組設定
- `IdentitiesOnly yes`：只使用指定的金鑰，不會亂試其他金鑰

> `~/.ssh/config` 存在自己的筆電上，不在專案裡，所以 IP 寫在這裡沒關係。

驗證（**不應該**再詢問密碼）：
```powershell
ssh jetson "whoami; hostname"
```

VS Code 也可以直接連進 Jetson 開發：安裝 **Remote - SSH** 擴充套件 → `F1` → `Remote-SSH: Connect to Host...` → 選 `jetson`。

### 0.8 隱私規則
這是**公開** repo，推上去的內容任何人都看得到，也可能被快取或建立索引，就算事後刪除也來不及。
- 程式碼和文件一律使用佔位符：`<jetson-ip>`、`<USER>`、`user@<jetson-ip>`
- 真實的 IP、帳號、密碼放在 `.env`（已經被 `.gitignore` 排除），或是 `~/.ssh/config` 這類本機檔案
- 不要用 `git commit --no-verify` 跳過隱私檢查，除非確定被擋下的內容沒有問題
- 已經不小心推上去的話：**先更換**外洩的密碼或金鑰，再處理 git 歷史紀錄

---

## Jetson 管理者：新增使用者
由有 sudo 權限的人在 Jetson 上執行：
```bash
sudo adduser <帳號>                          # 設定初始密碼，給使用者執行 0.6 時用
sudo usermod -aG video,docker <帳號>          # video：存取相機；docker：不必 sudo 就能執行 docker
```
- 使用者完成 0.6 之後，可以考慮關閉密碼登入，只允許金鑰：在 `/etc/ssh/sshd_config` 設定 `PasswordAuthentication no`，再執行 `sudo systemctl restart ssh`。關閉前，請先確認**所有人**都已經能用金鑰登入。
- 要撤銷某個人的權限：刪除他 `~/.ssh/authorized_keys` 裡對應的那一行。每一行最後的註解（例如 `<名字>@jetson-yolo-deploy`）可以用來辨識是誰的金鑰。

---

## 驗證
在專案資料夾執行，會在 Jetson 上跑環境檢查：
```powershell
type scripts\check_env.sh | ssh jetson "tr -d '\r' | sed '1s/^\xEF\xBB\xBF//' | bash -s"
```
> macOS / Linux：`ssh jetson 'bash -s' < scripts/check_env.sh`

有顯示 L4T、CUDA、TensorRT 等資訊，就代表連線設定完成。檢查結果怎麼看，請參考 [01-environment.md](01-environment.md)。

## 常見問題
| 狀況 | 原因 / 解法 |
|---|---|
| 放好公鑰還是會問密碼 | 1. `~/.ssh/config` 沒有設定 `IdentityFile`（見 0.7）<br>2. Jetson 上的權限太寬：`chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys`，家目錄不能讓其他人寫入<br>3. 用 `ssh -v jetson` 查看實際嘗試了哪些金鑰 |
| 腳本在 Jetson 上出現 `$'\r': command not found` | 用 PowerShell 管線傳送時少了 `tr -d '\r'`（見 0.6 / 驗證的寫法） |
| `Permission denied (publickey,password)` | 帳號名稱打錯，或是公鑰被放到別的帳號底下 |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | Jetson 重灌過，或是 IP 換了另一台機器。確認沒問題後執行 `ssh-keygen -R <jetson-ip>` |
| `Connection timed out` | 筆電和 Jetson 不在同一個網段，或是 Jetson 的 IP 變了（可以在 Jetson 上執行 `ip -4 addr` 查詢） |
| commit 被隱私檢查擋下 | 把被擋下的那一行改成佔位符，或把真實值移到 `.env` |
| `git push` 要求登入 | 執行 `gh auth login`，或是依照跳出的瀏覽器視窗登入 |

## 完成條件
- [ ] `git config user.email` 是 noreply 地址
- [ ] `git config core.hooksPath` 顯示 `.githooks`
- [ ] `ssh jetson` 可以免密碼登入
- [ ] 透過 SSH 執行 `check_env.sh` 有正常輸出
