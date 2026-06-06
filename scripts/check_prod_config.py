import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

files = {
    "docker-compose.prod.yml": ROOT / "docker-compose.prod.yml",
    "frontend/Dockerfile.prod": ROOT / "frontend" / "Dockerfile.prod",
    "frontend/src/App.jsx": ROOT / "frontend" / "src" / "App.jsx",
    "Caddyfile": ROOT / "Caddyfile",
    "frontend/nginx.conf": ROOT / "frontend" / "nginx.conf",
    ".env.example": ROOT / ".env.example",
}

missing = [name for name, path in files.items() if not path.exists() and name != "frontend/nginx.conf"]
if missing:
    raise SystemExit(f"Missing files: {', '.join(missing)}")

compose_text = files["docker-compose.prod.yml"].read_text(encoding="utf-8")
if "8000:8000" in compose_text:
    raise SystemExit("Prod compose should not expose 8000")
if "3306:3306" in compose_text:
    raise SystemExit("Prod compose should not expose 3306")
if "env_file" not in compose_text:
    raise SystemExit("Prod compose should use .env via env_file")
if "/var/lib/mysql" not in compose_text:
    raise SystemExit("Prod compose should mount a persistent volume for MySQL")
if "VITE_API_URL: /api" not in compose_text:
    raise SystemExit("Prod compose should build frontend with VITE_API_URL=/api")

for secret in ["rootpass", "emipass", "change-me"]:
    if secret in compose_text:
        raise SystemExit("Prod compose should not hardcode passwords or tokens")

web_text = files["frontend/Dockerfile.prod"].read_text(encoding="utf-8")
if "npm run build" not in web_text:
    raise SystemExit("Dockerfile.prod should build frontend assets")
if "npm run dev" in web_text or "vite" in web_text:
    raise SystemExit("Dockerfile.prod should not run Vite dev server")

app_text = files["frontend/src/App.jsx"].read_text(encoding="utf-8")
if "http://localhost:8000" in app_text:
    raise SystemExit("Frontend should not fall back to localhost in production")

caddy_path = files["Caddyfile"]
nginx_path = files["frontend/nginx.conf"]
proxy_found = False
if caddy_path.exists():
    caddy_text = caddy_path.read_text(encoding="utf-8")
    if "/api" in caddy_text and "reverse_proxy" in caddy_text:
        proxy_found = True
if nginx_path.exists():
    nginx_text = nginx_path.read_text(encoding="utf-8")
    if "/api" in nginx_text and "proxy_pass" in nginx_text:
        proxy_found = True
if not proxy_found:
    raise SystemExit("Proxy config must include /api reverse proxy")

env_text = files[".env.example"].read_text(encoding="utf-8")
required_keys = ["MYSQL_PASSWORD", "MYSQL_ROOT_PASSWORD", "ADMIN_UPLOAD_TOKEN", "DOMAIN"]
missing_keys = [key for key in required_keys if key not in env_text]
if missing_keys:
    raise SystemExit(f".env.example is missing keys: {', '.join(missing_keys)}")

print("Production config check passed")
