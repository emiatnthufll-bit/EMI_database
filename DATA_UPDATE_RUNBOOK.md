# EMI 資料更新操作手冊


使用情境：

```text
你已經把新的 Excel 放到本機專案的 backend/data/data.xlsx
```

接下來照下面步驟做即可。

## 1. 打開本機專案資料夾

在 PowerShell 輸入：

```powershell
cd C:\python\EMI
```

預期結果：

```text
沒有錯誤訊息，畫面停在 C:\python\EMI>
```

## 2. 確認 Excel 有更新

輸入：

```powershell
git status
```

預期結果：

```text
會看到 backend/data/data.xlsx
```

如果有看到 `.env`、`aws_password`、`.pem`，不要把它們上傳。

## 3. 把新的 Excel 上傳到 GitHub

輸入：

```powershell
git add backend/data/data.xlsx
git commit -m "Update production data"
git push shared main
```

預期結果：

```text
main -> main
```

意思是新的 Excel 已經上傳到公用 GitHub。

如果出現：

```text
nothing to commit
```

代表 Git 沒有偵測到 Excel 有變更，請確認檔案是否真的覆蓋到：

```text
C:\python\EMI\backend\data\data.xlsx
```

## 4. 登入 AWS 主機

在 PowerShell 輸入 SSH 指令。

範例：

```powershell
ssh -i "C:\Users\User\.ssh\LightsailDefaultKey-ap-northeast-2.pem" ubuntu@你的固定IP
```

預期結果：

```text
ubuntu@ip-...:~$
```

意思是你已經進入 AWS 主機。

## 5. 進入 AWS 上的 EMI 專案

在 AWS 畫面輸入：

```bash
cd ~/EMI
```

預期結果：

```text
ubuntu@ip-...:~/EMI$
```

## 6. 從 GitHub 下載最新版

輸入：

```bash
git pull
```

預期結果：

```text
Updating ...
```

或：

```text
Already up to date.
```

`Updating` 代表有下載到新版本。

`Already up to date` 代表 AWS 已經是最新版。

## 7. 重新啟動網站服務

輸入：

```bash
sudo docker compose -f docker-compose.prod.yml up -d --build
```

預期結果：

```text
Container emi_mysql Healthy
Container emi_api Started
Container emi_web Started
Container emi_caddy Started
```

## 8. 確認服務有正常啟動

輸入：

```bash
sudo docker compose -f docker-compose.prod.yml ps
```

預期結果：

```text
emi_mysql   Up (healthy)
emi_api     Up
emi_web     Up
emi_caddy   Up
```

只要四個容器都是 `Up`，就可以繼續。

## 9. 備份目前資料庫

輸入：

```bash
mkdir -p ~/EMI/backups
sudo docker compose -f docker-compose.prod.yml exec db sh -c 'mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' > ~/EMI/backups/emi-before-data-update-$(date +%Y%m%d-%H%M%S).sql
```

預期結果：

```text
沒有錯誤訊息
```

意思是舊資料已經備份起來。

## 10. 清空舊資料

輸入：

```bash
sudo docker compose -f docker-compose.prod.yml exec -T db sh <<'SH'
set -eu

for table in \
  paper_publication_types \
  paper_journal_indices \
  paper_study_natures \
  paper_education_levels \
  paper_research_locations \
  paper_research_focuses \
  paper_categories \
  paper_keywords \
  papers \
  publication_types \
  journal_indices \
  study_natures \
  education_levels \
  research_locations \
  research_focuses \
  categories \
  keywords
do
  exists=$(mysql -u root -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" -Nse "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = '$table';")
  if [ "$exists" = "1" ]; then
    mysql -u root -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" -e "SET FOREIGN_KEY_CHECKS=0; TRUNCATE TABLE \`$table\`; SET FOREIGN_KEY_CHECKS=1;"
    echo "truncated $table"
  fi
done
SH
```

預期結果：

```text
truncated papers
truncated ...
```

意思是舊資料已清空。

## 11. 把新的 Excel 放進後端容器

輸入：

```bash
sudo docker cp backend/data/data.xlsx emi_api:/tmp/data.xlsx
```

預期結果：

```text
沒有錯誤訊息
```

這一步是把新的 Excel 交給後端程式讀取。

## 12. 匯入新的 Excel

輸入：

```bash
sudo docker compose -f docker-compose.prod.yml exec api python -c "from app.data_loader import load_data; print(load_data('/tmp/data.xlsx'))"
```

預期結果：

```text
'ok': True
'errors': []
```

如果資料有 7 筆，也會看到：

```text
'total_rows': 7
'inserted': 7
```

之後資料筆數變多時，數字會不一樣，這是正常的。

## 13. 確認資料庫筆數

輸入：

```bash
sudo docker compose -f docker-compose.prod.yml exec db sh -c 'mysql -u root -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" -e "SELECT COUNT(*) AS paper_count FROM papers;"'
```

預期結果：

```text
paper_count
7
```

數字應該要等於 Excel 裡有效的文章筆數。

## 14. 打開網站檢查

用瀏覽器打開網站。

請檢查：

```text
有搜尋結果
左邊篩選欄有選項
右邊文章細節有顯示
標題可以點到 DOI
```

如果都正常，資料更新完成。

## 常見問題

### A. 匯入時出現 File not found

如果看到：

```text
File not found: /app/data/data.xlsx
```

請改用這兩行：

```bash
sudo docker cp backend/data/data.xlsx emi_api:/tmp/data.xlsx
sudo docker compose -f docker-compose.prod.yml exec api python -c "from app.data_loader import load_data; print(load_data('/tmp/data.xlsx'))"
```

### B. 密碼錯誤

如果看到：

```text
Access denied
```

請確認你是在 AWS 主機上操作，不是本機 PowerShell。

也可以使用這種不用手動輸入密碼的指令：

```bash
sudo docker compose -f docker-compose.prod.yml exec db sh -c 'mysql -u root -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"'
```

### C. 網站還是舊資料

通常是沒有清空舊資料，或沒有重新匯入。

請重新執行：

```text
第 10 步：清空舊資料
第 11 步：把新的 Excel 放進後端容器
第 12 步：匯入新的 Excel
第 13 步：確認資料庫筆數
```

### D. 想還原到更新前

先找備份檔：

```bash
ls -lh ~/EMI/backups
```

再還原：

```bash
cd ~/EMI
sudo docker compose -f docker-compose.prod.yml exec -T db sh -c 'mysql -u root -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' < backups/備份檔名.sql
```

把 `備份檔名.sql` 換成實際看到的檔名。
