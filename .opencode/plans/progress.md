# Progress: Fix scriptureengine.org SSL Handshake Failure

## Session 2026-07-22
- **Current phase:** Track A / Phase A1 (not started)
- **Plan created:** task_plan.md + findings.md written
- **Status:** Waiting for execution

## Summary of Diagnosed Issues

1. **nginx removed, Caddy installed** — nginx was replaced by Caddy (Docker) but scriptureengine.org was never migrated
2. **API binds to 127.0.0.1** — unreachable from Docker containers
3. **No Caddy site block** — Caddy has no config for scriptureengine.org, causing TLS handshake failure
4. **VPS.md + deploy.sh outdated** — both reference nginx which no longer exists

## Key Decisions Made

- Bind API to `0.0.0.0` (was `127.0.0.1`)
- Add scriptureengine.org to existing Caddy deployment
- Use `host.docker.internal` for Caddy-to-host connectivity
- Update VPS.md and deploy.sh
