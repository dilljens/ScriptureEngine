# Findings: Fix scriptureengine.org SSL Handshake Failure

## Root Cause

The VPS at `40.160.241.74` originally used **nginx** as its reverse proxy (documented in VPS.md), but nginx has since been **removed** and replaced by **Caddy v2** running as a Docker container (`ferrum-caddy`) deployed via the `sololedger` project's docker-compose at `/opt/sololedger/deploy/docker-compose.yml`.

The existing Caddyfile only has site blocks for:
- `sololedger.ferrumeng.com` → `sololedger-api:8100`
- `poolsplat.ferrumeng.com` → `poolsplat:3138`

**No site block exists for `scriptureengine.org`.** Cloudflare (proxied/orange cloud) connects to the origin on port 443, Caddy accepts the connection but can't complete the TLS handshake because it has no certificate for `scriptureengine.org`, resulting in the "SSL handshake failed" error.

## Current Working State

| Component | Status | Details |
|-----------|--------|---------|
| `scripture-api` systemd service | ✅ Running | uvicorn on `127.0.0.1:8000` — health check returns 200 |
| Frontend dist | ✅ Present | `/var/www/scripture/frontend/dist/` — includes `index.html`, JS, assets |
| API code & lib | ✅ Present | `/var/www/scripture/web/`, `/var/www/scripture/lib/` |
| Database | ✅ Present | `/var/www/scripture/scripture.db` (1.4GB) |
| Let's Encrypt cert | ✅ Valid | `scriptureengine.org` + `www.scriptureengine.org` — expires Sep 22, 2026 |
| nginx | ❌ Not installed | `/etc/nginx/` does not exist |
| Caddy as reverse proxy | ⚠️ Missing config | Runs on ports 80/443 but has no `scriptureengine.org` site block |

## Infrastructure Changes Since VPS.md

The server has evolved beyond what VPS.md documents. New projects deployed:
- **SoloLedger** (`sololedger.ferrumeng.com`) — FastAPI + SPA served via Caddy
- **PoolSplat** (`poolsplat.ferrumeng.com`) — 3D viewer served via Caddy
- **Netdata** — system monitoring container

## Pre-resolved Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| API binding | Change to `0.0.0.0:8000` | Simplest change — API is behind Cloudflare proxy, exposure risk minimal |
| Reverse proxy config | Add to Caddyfile | Caddy is already running and handling all other domains |
| Docker-to-host connectivity | `extra_hosts: ["host.docker.internal:host-gateway"]` | Standard pattern for Docker-to-host access |
| Frontend serving | Volume mount into Caddy container | Caddy handles static files directly (faster than proxying to uvicorn) |
| VPS.md | Update to reflect current Caddy-based architecture | Docs must match reality |

## Architecture After Fix

```
User → Cloudflare (proxied) → VPS :443 → Caddy
  ├── sololedger.ferrumeng.com → sololedger-api:8100
  ├── poolsplat.ferrumeng.com  → poolsplat:3138
  └── scriptureengine.org
      ├── /api/*    → host.docker.internal:8000 (uvicorn, 2 workers)
      └── /*        → /var/www/scripture/frontend/dist/ (static SPA)
```

## Outdated nginx deployment in deploy.sh

The deploy script still tries to sync and reload nginx. These steps silently fail because nginx isn't installed. The script needs updating to no longer reference nginx, and potentially to reload Caddy config instead.
