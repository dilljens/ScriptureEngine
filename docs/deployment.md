# ScriptureEngine — Deployment

> Hosted on Hetzner CX23 (`46.224.171.239`) alongside Inklomancer.

## Architecture

### ScriptureEngine
```
https://scriptureengine.org
  └── nginx (:443)
      ├── /api/* → reverse proxy → uvicorn (:8000, 2 workers)
      ├── /docs, /openapi.json → proxy → uvicorn
      └── /* → /var/www/scripture/frontend/dist/index.html (SPA)
```

### Inklomancer
```
https://inklomancer.com
  └── nginx (:443)
      ├── / → static SPA files (/var/www/inklomancer/dist/)
      ├── /ws → WebSocket proxy → node (:3001)
      └── /* → index.html (SPA)
```

## Server Info

| Detail | Value |
|--------|-------|
| Host | Hetzner CX23 |
| IP | `46.224.171.239` |
| RAM | 4 GB |
| CPU | 2 vCPUs |
| OS | Ubuntu |
| Cost | ~€4.49/month |

## One-Time Server Setup

```bash
# SSH into server
ssh root@46.224.171.239

# Install Python deps
apt install python3 python3-pip python3-venv

# Create app directories
mkdir -p /var/www/scripture
mkdir -p /var/www/inklomancer

# Copy env files
echo 'DEEPSEEK_API_KEY="sk-..."' > /var/www/scripture/.env
```

## Deploy

### ScriptureEngine
```bash
./scripts/deploy.sh
```
Builds the React frontend, rsyncs `frontend/dist/`, `web/`, `lib/`, and `data/` 
to the server, installs Python deps, copies nginx + systemd configs, and restarts.

**Note:** The deploy script now also syncs `scripts/nginx-scripture.conf` and 
`scripts/scripture-api.service` to the server automatically.

### Inklomancer
```bash
cd /home/dillon/_code/inklomancer && ./scripts/deploy.sh
```
Builds the frontend, rsyncs `dist/` and `server/`, copies nginx + systemd configs.

### DNS Setup (Cloudflare)

| Domain | Type | Value |
|--------|------|-------|
| `scriptureengine.org` | A | `46.224.171.239` (DNS only) |
| `www.scriptureengine.org` | CNAME | `scriptureengine.org` |
| `inklomancer.com` | A | `46.224.171.239` (DNS only) |
| `www.inklomancer.com` | CNAME | `inklomancer.com` |

Set to **DNS only** (grey cloud) initially so Let's Encrypt can verify the domain.
After SSL certs are issued, you can switch to Proxied (orange cloud) for CDN benefits.

### SSL Certificates
```bash
# After DNS is pointing to the server:
ssh root@46.224.171.239
certbot --nginx -d scriptureengine.org -d www.scriptureengine.org
certbot --nginx -d inklomancer.com -d www.inklomancer.com
```

## Services

### ScriptureEngine — systemd: `scripture-api`
| Detail | Value |
|--------|-------|
| Port | 8000 (localhost only) |
| Workers | 2 (uvicorn --workers 2) |
| RAM cache | ~1GB per worker (both loaded at startup) |
| Env file | `/var/www/scripture/.env` (DEEPSEEK_API_KEY) |

### Inklomancer — systemd: `inklomancer-server`
| Detail | Value |
|--------|-------|
| Port | 3001 (localhost only) |
| Runtime | Node.js via `npx tsx` |
| Protocol | WebSocket (`wss://inklomancer.com/ws`) |

### nginx
| Domain | Config file | Site enabled |
|--------|------------|--------------|
| `scriptureengine.org` | `/etc/nginx/sites-available/scriptureengine` | Yes |
| `inklomancer.com` | `/etc/nginx/sites-available/inklomancer` | Yes |

## Configuration Files

| File | App | Purpose |
|------|-----|---------|
| `scripts/deploy.sh` | SE | Build + deploy |
| `scripts/scripture-api.service` | SE | systemd unit for FastAPI |
| `scripts/nginx-scripture.conf` | SE | nginx site config |
| `docs/deployment.md` | SE | This file |
| `scripts/nginx-inklomancer.conf` | Inkl | nginx site config |
| `scripts/inklomancer-server.service` | Inkl | systemd unit for game server |
| `scripts/deploy.sh` | Inkl | Build + deploy |

## Ports

| Port | Service | Access |
|------|---------|--------|
| 443 | nginx (HTTPS) | Public — both domains |
| 80 | nginx (HTTP) | Public — redirects to 443 |
| 8000 | uvicorn (SE) | Localhost only |
| 3001 | Node.js (Inkl) | Localhost only |
| 8443 | Daglock indexer | Localhost only |

## Resources on CX23 (4GB RAM)

| Process | RAM |
|---------|-----|
| 2× uvicorn workers (cached) | ~2GB |
| Inklomancer game server | ~300MB |
| nginx + OS | ~500MB |
| **Total** | **~2.8GB** |
| **Headroom** | **~1.2GB** |
