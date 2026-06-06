# EMI Literature Database

EMI is a literature search and management system for EMI research in the language education domain. The system supports fulltext search, filters, Excel import, and Docker-based deployment.

## Project Overview

- Stack: React 18 + Vite + Tailwind CSS, FastAPI + PyMySQL, MySQL 8.0
- Data: Excel import (pandas + openpyxl) -> MySQL -> web search
- Search: title / abstract / authors fulltext search with ngram parser

## Local Development

### Start

```powershell
cd c:\python\EMI
docker compose up --build
```

### Services

- Web: http://localhost:5173
- API: http://localhost:8000
- API docs: http://localhost:8000/docs
- DB: localhost:3306

### Stop

```powershell
docker compose down
```

## Excel Import

### Admin upload page

- Go to http://localhost:5173/admin
- Enter the admin token
- Select a .xlsx file
- Upload and check import result

### API upload

```
POST /admin/upload-excel
Header: X-Admin-Token: <token>
Body: multipart/form-data (file=.xlsx)
```

### Excel format (fixed)

This Excel format is fixed by the supervisor. The importer reads with `header=4`.

Column mapping:

- Code = Article ID / paper code
- Unnamed: 1 = Authors
- Unnamed: 2 = Year
- Unnamed: 3 = Title
- Unnamed: 4 = Journal / Venue
- Unnamed: 5 = DOI
- Unnamed: 6 = WebLink / URL
- Unnamed: 7 = Citation / APA Citation
- Unnamed: 8 = Abstract

Metadata code columns:

BC, B, JA,
SSCI, AHCI, ESCI, LLBA, SCOPUS, THSS,
RE, PD, SQ, IN, CO, TS, CS,
HE, KS,
TW, CN, HK, AS, EU, OTH, AR,
TO, SO, EP, EL, CL, TT, CD, TM, RL, SI, RM

## Admin Token

Set `ADMIN_UPLOAD_TOKEN` in docker-compose or .env.

## Testing

### Start test environment

```powershell
cd c:\python\EMI
docker compose up -d
```

### Backend tests

The tests use a separate MySQL database named `emi_test_db` and do not touch production data.

```powershell
cd c:\python\EMI\backend
pytest
```

Unit tests (helpers only):

```powershell
cd c:\python\EMI\backend
pytest -k helpers
```

Integration tests (ingest, API, search):

```powershell
cd c:\python\EMI\backend
pytest -k "data_loader or upload or search"
```

Optional env overrides:

- `TEST_DB_HOST` (default: localhost)
- `TEST_DB_PORT` (default: 3306)
- `TEST_DB_USER` (default: root)
- `TEST_DB_PASSWORD` (default: rootpass)
- `TEST_DB_NAME` (default: emi_test_db)
- `TEST_ADMIN_TOKEN` (default: test-token)

### Smoke test

```bash
bash scripts/test_smoke.sh
```

### Excel upload test (manual)

1. Open http://localhost:5173/admin
2. Enter token
3. Upload a .xlsx
4. Confirm inserted / updated / skipped counts

### Upsert test (manual)

1. Upload the same Excel twice
2. Confirm total papers does not double

### Backup test

```bash
bash scripts/backup_mysql.sh
```

For local development with `docker-compose.yml`, run:

```bash
COMPOSE_FILE=./docker-compose.yml bash scripts/backup_mysql.sh
```

Check `backups/` for a new `.sql.gz` file and verify size > 0.

### Backup restore test

```bash
bash scripts/test_restore_backup.sh
```

For local development with `docker-compose.yml`, run:

```bash
COMPOSE_FILE=./docker-compose.yml bash scripts/test_restore_backup.sh
```

### Production config check

```bash
python scripts/check_prod_config.py
```

### Full CI-style check

```bash
bash scripts/run_all_checks.sh
```

PowerShell version:

```powershell
scripts\run_all_checks.ps1
```

## Production Deployment

### Recommended AWS path: Lightsail VPS

For the current EMI workload, start with a small AWS Lightsail Ubuntu instance and run the existing Docker Compose production stack on one VM.

Suggested first setup:

- Instance: Ubuntu 22.04 or 24.04 LTS
- Size: at least 2 GB RAM
- Networking: attach a static IP, open ports 80 and 443
- DNS: create an A record for your domain pointing to the Lightsail static IP
- Runtime: Docker Engine + Docker Compose plugin

Server setup outline:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

Log out and log back in so the Docker group change takes effect, then clone or upload this project to the server.

1. Copy and edit env file

```
cp .env.example .env
```

Set strong values for:

- `MYSQL_ROOT_PASSWORD`
- `MYSQL_PASSWORD`
- `ADMIN_UPLOAD_TOKEN`
- `DOMAIN`

2. Deploy

```
docker compose -f docker-compose.prod.yml up -d --build
```

This setup targets a normal VPS/VM (e.g., Ubuntu + Docker Compose). It uses Caddy as the reverse proxy:

- / -> frontend (static)
- /api -> backend

Useful production checks:

```bash
python scripts/check_prod_config.py
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f caddy api
```

## Backup

```bash
bash scripts/backup_mysql.sh
```

Example cron (daily at 03:00):

```
0 3 * * * /path/to/EMI/scripts/backup_mysql.sh
```

## Migration SQL

Run these once if your `papers` table is missing columns or indexes:

```sql
ALTER TABLE papers ADD COLUMN article_code VARCHAR(50);
ALTER TABLE papers ADD UNIQUE KEY uk_papers_article_code (article_code);
ALTER TABLE papers ADD COLUMN citation TEXT;
ALTER TABLE papers ADD INDEX idx_papers_doi (doi);
ALTER TABLE papers ADD INDEX idx_papers_title_year (title, year);
```

## Notes

- Do not edit MySQL data manually. Update via Excel upload.
- Back up before each import when running in production.
- [ ] Integration with Meilisearch/Elasticsearch for BM25
- [ ] Spell correction
- [ ] CSV/JSON batch import
- [ ] User authentication and roles
- [ ] Paper submission workflow
- [ ] Citation management
- [ ] Export functionality

## 📝 License

This project is for educational and research purposes.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Contact

For questions or issues, please open an issue on the repository.
