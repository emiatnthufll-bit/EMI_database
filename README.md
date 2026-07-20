# EMI Literature Database

EMI Literature Database 是一套用於整理、搜尋與篩選 EMI / CLIL 文獻資料的網站系統。維護者主要透過 Excel 更新資料，系統會將 Excel 匯入 MySQL，並提供網頁搜尋、左側分類篩選與文章細節檢視。

## 目前系統功能

- 文獻搜尋：支援標題、摘要、作者關鍵字搜尋
- 左側篩選：依 Paper Type、Research Topics、Research Results、Research Methods、Research Setting、Participants 篩選
- 文章細節：顯示 Paper Title、Authors、Year、Publication Details、Journal Quality、Abstract
- DOI 連結：文章標題可連到 DOI 頁面
- Excel 匯入：支援目前新版資料格式 `backend/data/data.xlsx`
- Docker 部署：本機開發與 AWS Lightsail 上線皆使用 Docker Compose

## 系統架構

```text
使用者瀏覽器
  |
  v
Caddy / Nginx reverse proxy
  |-- 前端 React / Vite
  |-- 後端 FastAPI
        |
        v
      MySQL 8.0
```

正式部署時共有四個主要容器：

| 容器 | 用途 |
| --- | --- |
| `emi_caddy` | 對外入口，負責 80/443、HTTPS、把 `/api` 轉給後端 |
| `emi_web` | 前端網站，提供搜尋頁、篩選欄、Admin 上傳頁 |
| `emi_api` | 後端 API，處理搜尋、篩選、Excel 匯入 |
| `emi_mysql` | MySQL 資料庫，保存文獻資料與分類標籤 |

## 專案目錄

```text
EMI/
  backend/
    app/
      main.py              # FastAPI API 入口
      data_loader.py       # Excel 讀取與匯入邏輯
      db.py                # MySQL 連線
      query_builder.py     # 搜尋條件組合
    data/
      data.xlsx            # 正式資料來源 Excel
    tests/                 # 後端測試
    Dockerfile

  frontend/
    src/
      App.jsx              # 主要搜尋介面
      AdminUpload.jsx      # Excel 上傳介面
    public/
    Dockerfile
    Dockerfile.prod

  mysql/
    init/01_schema.sql     # MySQL 初始資料表
    my.cnf                 # MySQL 設定

  scripts/
    check_prod_config.py   # 上線前設定檢查
    backup_mysql.sh        # 資料庫備份
    run_all_checks.*       # 測試與檢查腳本

  docker-compose.yml       # 本機開發環境
  docker-compose.prod.yml  # AWS / production 環境
  Caddyfile                # production reverse proxy 設定
  DATA_UPDATE_RUNBOOK.md   # 給維護者的資料更新手冊
  LIGHTSAIL_GO_LIVE.md     # Lightsail 上線流程筆記
```

## Excel 資料格式

正式資料檔位置：

```text
backend/data/data.xlsx
```

目前新版 Excel 主要欄位：

| 欄位 | 網頁顯示位置 |
| --- | --- |
| `Paper ID` | 系統內部辨識用，不顯示在網頁 |
| `Paper Title` | 右側文章標題，若有 DOI 可點擊 |
| `Authors` | 右側作者 |
| `Year` | 右側年份 |
| `Publication Details` | 右側出版資訊 |
| `DOI` | 用來產生標題連結，不單獨顯示 |
| `Journal Quality` | 右側期刊品質 |
| `Abstract` | 右側摘要 |

左側篩選欄位來自 Excel 中的分類欄位：

- Paper Type
- Research Topics
- Research Results
- Research Methods
- Research Setting
- Participants

維護者只需要更新 `backend/data/data.xlsx`，再依照 [DATA_UPDATE_RUNBOOK.md](DATA_UPDATE_RUNBOOK.md) 操作即可。

## 本機開發

### 啟動

```powershell
cd C:\python\EMI
docker compose up --build
```

### 開啟網站

```text
前端網站：http://localhost:5173
Admin 頁面：http://localhost:5173/admin
後端 API：http://localhost:8000
API 文件：http://localhost:8000/docs
MySQL：localhost:3306
```

### 停止

```powershell
docker compose down
```

## 本機匯入 Excel

開發環境會把 `backend/data` 掛進 API container，所以可以直接匯入：

```powershell
docker compose exec api python -c "from app.data_loader import load_data; print(load_data('/app/data/data.xlsx'))"
```

成功時會看到：

```text
'ok': True
'errors': []
```

也可以從 Admin 頁面上傳：

```text
http://localhost:5173/admin
```

Admin token 由 `ADMIN_UPLOAD_TOKEN` 設定。

## AWS / Production 部署

目前建議部署方式：

```text
AWS Lightsail Ubuntu + Docker Compose + Caddy + MySQL
```

基本需求：

- Ubuntu 22.04 LTS 或 24.04 LTS
- Docker Engine
- Docker Compose
- Lightsail Static IP
- 開放 80 / 443 port

Production 啟動：

```bash
cd ~/EMI
python3 scripts/check_prod_config.py
sudo docker compose -f docker-compose.prod.yml up -d --build
sudo docker compose -f docker-compose.prod.yml ps
```

確認四個容器都正常：

```text
emi_mysql   Up (healthy)
emi_api     Up
emi_web     Up
emi_caddy   Up
```

Production 資料更新請看：

```text
DATA_UPDATE_RUNBOOK.md
```

注意：production 的 API container 沒有直接掛載 `backend/data`，因此資料更新時需要先把 Excel copy 到 container，再執行匯入。這個流程已寫在 `DATA_UPDATE_RUNBOOK.md`。

## 環境變數

`.env` 不會上傳到 GitHub，請在每台機器自行建立。

可參考：

```bash
cp .env.example .env
```

必要設定：

| 變數 | 用途 |
| --- | --- |
| `MYSQL_ROOT_PASSWORD` | MySQL root 密碼 |
| `MYSQL_DATABASE` | 資料庫名稱，預設 `emi_db` |
| `MYSQL_USER` | API 使用的 MySQL 帳號 |
| `MYSQL_PASSWORD` | API 使用的 MySQL 密碼 |
| `ADMIN_UPLOAD_TOKEN` | Admin 上傳 Excel 所需 token |
| `DOMAIN` | production 網域或 `:80` |

不要提交到 GitHub：

```text
.env
aws_password
*.pem
```

## 測試

後端測試：

```powershell
cd C:\python\EMI\backend
pytest
```

前端 build 測試：

```powershell
cd C:\python\EMI\frontend
npm install
npm run build
```

Production 設定檢查：

```bash
python scripts/check_prod_config.py
```

完整檢查：

```bash
bash scripts/run_all_checks.sh
```

PowerShell 版本：

```powershell
scripts\run_all_checks.ps1
```

## 備份

Production 更新資料前，請先備份 MySQL。

```bash
mkdir -p ~/EMI/backups
sudo docker compose -f docker-compose.prod.yml exec db sh -c 'mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' > ~/EMI/backups/emi-before-data-update-$(date +%Y%m%d-%H%M%S).sql
```

備份與還原流程也整理在：

```text
DATA_UPDATE_RUNBOOK.md
```

## GitHub 使用方式

目前通常有兩個 remote：

```text
origin  個人 repo
shared  共用 repo
```

查看 remote：

```powershell
git remote -v
```

推到個人 repo：

```powershell
git push origin main
```

推到共用 repo：

```powershell
git push shared main
```

一般維護者更新正式資料時，主要推到共用 repo：

```powershell
git add backend/data/data.xlsx
git commit -m "Update production data"
git push shared main
```

## 維護注意事項

- 不要把 `.env`、`aws_password`、`.pem` 上傳到 GitHub
- 一般 Excel / PowerPoint 暫存檔已被 `.gitignore` 忽略
- `backend/data/data.xlsx` 是正式資料檔，仍可被 Git 追蹤與更新
- 更新 production 資料前要先備份資料庫
- 如果網站顯示舊資料，通常是 AWS 還沒 `git pull`、還沒清空舊資料，或還沒重新匯入 Excel
- 如果改到資料表欄位、Excel 欄位或前端顯示，請同步更新本 README 與 `DATA_UPDATE_RUNBOOK.md`

## License

This project is for educational and research purposes.
