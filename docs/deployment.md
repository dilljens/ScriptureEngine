# ScriptureEngine — Deployment

> Hosted on VPS (`40.160.241.74`) alongside Inklomancer.

## Reproduction from Git

To recreate this project from a fresh checkout, you need these things that are
**NOT tracked in git**:

| What | Why not tracked | How to get it |
|------|----------------|---------------|
| `data/processed/scripture.db` (1.8 GB) | Too large + binary | Run `scripts/build_all.sh` (runs all ingest/seed scripts in order) OR copy from a running instance |
| `data/audio/verses/*.wav` | Large binary files | Run `scripts/generate_audio.py` (TTS generation) |
| `data/audio/raw/*.mp3` | Large binary files | Download Shmueloff recordings from Archive.org or Mechon Mamre, place in `data/audio/raw/` |
| `data/audio/alignments/*.json` | Derived from audio | Run `scripts/align_hebrew_hybrid.py --chapter gen_1` (and for each chapter) |
| `data/raw/` (cloned repos) | External sources | Cloned by `scripts/setup.sh` |
| `.env` | Contains secrets | Create with `DATABASE_PATH=data/processed/scripture.db` |
| `.venv/` | Platform-specific | `python3 -m venv .venv && .venv/bin/pip install -r web/requirements.txt` |
| `frontend/node_modules/` | Platform-specific | `cd frontend && npm install` |
| `frontend/dist/` | Build artifact | `cd frontend && npx vite build` |

### The minimum to get running (API only, no audio):
```bash
git clone https://github.com/dilljens/ScriptureEngine.git
cd ScriptureEngine
python3 -m venv .venv
.venv/bin/pip install -r web/requirements.txt
# Obtain scripture.db from a running instance or build it
cp /path/to/existing/scripture.db data/processed/
# Start API
.venv/bin/uvicorn web.server:app --host 0.0.0.0 --port 8000
```

### Full rebuild from source data:
```bash
# Will set up VENV, clone repos, build DB, generate audio, etc.
bash scripts/build_all.sh
# Or step by step:
bash scripts/setup.sh              # Clone external data sources
bash scripts/ingest_all.sh         # Build scripture.db from source texts
bash scripts/seed_all.sh           # Run connection generators
bash scripts/generate_audio.py     # Generate TTS audio
bash scripts/align_hebrew_hybrid.py --chapter gen_1  # Align audio
```

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
| IP | `40.160.241.74` |
| RAM | 4 GB |
| CPU | 2 vCPUs |
| OS | Ubuntu |
| Cost | ~€4.49/month |

## One-Time Server Setup

```bash
# SSH into server
ssh root@40.160.241.74

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
| `scriptureengine.org` | A | `40.160.241.74` (DNS only) |
| `www.scriptureengine.org` | CNAME | `scriptureengine.org` |
| `inklomancer.com` | A | `40.160.241.74` (DNS only) |
| `www.inklomancer.com` | CNAME | `inklomancer.com` |

Set to **DNS only** (grey cloud) initially so Let's Encrypt can verify the domain.
After SSL certs are issued, you can switch to Proxied (orange cloud) for CDN benefits.

### SSL Certificates
```bash
# After DNS is pointing to the server:
ssh root@40.160.241.74
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
