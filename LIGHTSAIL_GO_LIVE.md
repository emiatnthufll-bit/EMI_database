# EMI Lightsail Go-Live Checklist

Use this checklist before deploying EMI to AWS Lightsail.

## 1. Decide the public domain

Choose the domain or subdomain that will serve EMI, for example:

```text
emi.your-domain.com
```

Then update `.env`:

```env
DOMAIN=emi.your-domain.com
```

Do not leave `DOMAIN=emi.example.com` for production.

## 2. Create the Lightsail instance

Recommended starting point:

- Platform: Linux/Unix
- Blueprint: Ubuntu 22.04 LTS or Ubuntu 24.04 LTS
- Plan: at least 2 GB RAM
- Region: choose the region closest to your main users

After creating the instance:

- Create and attach a Lightsail static IP
- Open inbound TCP ports `80` and `443`
- Keep SSH port `22` limited to your own IP if possible

## 3. Point DNS to Lightsail

In your DNS provider, create an A record:

```text
Type: A
Name: emi
Value: <Lightsail static IP>
TTL: 300
```

If the domain itself should point to EMI, use:

```text
Type: A
Name: @
Value: <Lightsail static IP>
TTL: 300
```

Wait for DNS propagation before starting Caddy HTTPS setup.

## 4. Install Docker on the server

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

Log out and log back in before running Docker commands.

## 5. Upload or clone the project

Put this project on the server, for example:

```bash
git clone <your-repo-url> EMI
cd EMI
```

If the project is uploaded manually, make sure these files are present:

- `.env`
- `docker-compose.prod.yml`
- `Caddyfile`
- `backend/`
- `frontend/`
- `mysql/`

## 6. Validate production config

```bash
python3 scripts/check_prod_config.py
```

If Python is not installed:

```bash
sudo apt install -y python3
```

## 7. Start production

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Check status:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f caddy api
```

## 8. Import or restore data

Option A: use the admin upload page:

```text
https://your-domain/admin
```

Use `ADMIN_UPLOAD_TOKEN` from `.env`.

Option B: restore from a MySQL backup if you already have one.

## 9. Set up backups

Create a daily cron job:

```bash
crontab -e
```

Add:

```cron
0 3 * * * /path/to/EMI/scripts/backup_mysql.sh
```

Periodically copy backups off the Lightsail instance.

## 10. Final smoke test

Open:

```text
https://your-domain/
https://your-domain/api/health
https://your-domain/admin
```

Confirm:

- The homepage loads over HTTPS
- Search requests return results
- `/api/health` returns `{"ok": true}`
- Admin upload rejects a wrong token
- Admin upload accepts the real token
- Data persists after `docker compose -f docker-compose.prod.yml restart`

