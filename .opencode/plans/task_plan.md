# Fix scriptureengine.org SSL Handshake Failure

Goal: Restore HTTPS access to `scriptureengine.org` by adding its reverse-proxy configuration to Caddy (which replaced nginx on the VPS).

## Requirements

- [ ] R1: `scriptureengine.org` and `www.scriptureengine.org` serve HTTPS correctly (no SSL errors)
- [ ] R2: API at `/api/*` routes to the uvicorn backend (port 8000)
- [ ] R3: Static SPA frontend is served for all other routes (`/*`)
- [ ] R4: Caddy auto-manages HTTPS certificates (auto-renewal)
- [ ] R5: VPS.md reflects the current Caddy-based architecture

## Pre-resolved Decisions

See `findings.md` — all decisions documented there.

---

## Track A: Configure Caddy + API for scriptureengine.org `[ ]`

Single track covering everything needed to restore the site.

### Phase A1: Update API binding to 0.0.0.0 `[ ]`
- **Priority:** high
- **Max turns:** 3
- [ ] Edit `/etc/systemd/system/scripture-api.service` on the VPS: change `--host 127.0.0.1` to `--host 0.0.0.0`
- [ ] Reload systemd and restart: `systemctl daemon-reload && systemctl restart scripture-api`
- **📏 Scope:** 1 file (service file), 1 line changed
- **✅ Checkpoint:** `curl -s http://172.19.0.1:8000/api/v1/health` returns `{"ok":true,...}` (verify reachable from Docker bridge)
- **⚙ Fallback:** If `0.0.0.0` causes issues, bind to the specific Docker bridge IP `172.19.0.1` instead

### Phase A2: Add scriptureengine.org to Caddy config `[ ]`
- **Priority:** high
- **Max turns:** 5
- [ ] Edit `/opt/sololedger/deploy/Caddyfile` — add site block for `scriptureengine.org, www.scriptureengine.org`
- [ ] Add handle for `/api/*` → reverse_proxy `host.docker.internal:8000`
- [ ] Add handle for `/*` → root `/var/www/scripture` + try_files/index.html fallback
- [ ] Edit `/opt/sololedger/deploy/docker-compose.yml`:
  - Add `extra_hosts: ["host.docker.internal:host-gateway"]` to caddy service
  - Add volume mount: `- /var/www/scripture/frontend/dist:/var/www/scripture:ro`
- [ ] Restart Caddy: `docker compose -f /opt/sololedger/deploy/docker-compose.yml up -d caddy`
- **📏 Scope:** 2 files compose + Caddyfile, ~30 lines added
- **✅ Checkpoint:** `curl -s -o /dev/null -w "%{http_code}" https://scriptureengine.org/api/v1/health` returns 200
- **⚙ Fallback:** If `host.docker.internal` isn't available, use `172.19.0.1:8000` directly in the Caddyfile

### Phase A3: Verify full site functionality `[ ]`
- **Priority:** high
- **Max turns:** 3
- [ ] Test HTTPS: `curl -sI https://scriptureengine.org` — returns 200 with SPA HTML
- [ ] Test API: `curl -s https://scriptureengine.org/api/v1/health` — returns 200 with health JSON
- [ ] Test www redirect: `curl -sI https://www.scriptureengine.org` — works (Caddy auto-handles)
- [ ] Check Caddy logs for errors: `docker logs ferrum-caddy --tail 30`
- **📏 Scope:** Verification only, no file changes
- **✅ Checkpoint:** Browser test or full curl suite passes
- **⚙ Fallback:** If partial failure, check Caddy logs and adjust config

### Phase A4: Update deploy.sh (remove stale nginx steps) `[ ]`
- **Priority:** medium
- **Max turns:** 3
- [ ] Option A: Remove nginx-specific lines from `scripts/deploy.sh`
- [ ] Option B: Add Caddy config reload via `docker compose restart caddy` instead
- **📏 Scope:** 1 file, ~10 lines changed
- **✅ Checkpoint:** `grep -c nginx scripts/deploy.sh` returns 0 (or only comments)
- **⚙ Fallback:** Skip if risky — nginx lines fail silently with `||`

### Phase A5: Update VPS.md to reflect current architecture `[ ]`
- **Priority:** medium
- **Max turns:** 3
- [ ] Update Scripture Engine section: replace nginx references with Caddy
- [ ] Update Services Map diagram to show Caddy as reverse proxy
- [ ] Remove nginx from the systemd services list (it's not installed)
- [ ] Update SSL section to note Caddy handles certs (but LE certs still exist)
- [ ] Add sololedger and poolsplat to the project list
- **📏 Scope:** 1 file, ~30 lines changed
- **✅ Checkpoint:** VPS.md no longer mentions nginx for scriptureengine.org
- **⚙ Fallback:** N/A — docs change only
