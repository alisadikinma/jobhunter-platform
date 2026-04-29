# GitHub Actions — JobHunter CI/CD

Two workflows:

- **`ci.yml`** — runs on every push & PR to `master`. Postgres 16 service, alembic migrations, ruff, mypy, pytest. No deploy gate.
- **`deploy.yml`** — runs on every push to `master` (and manual dispatch). SSHes into the production VPS and runs `scripts/deploy.sh`, which:
  1. `git fetch + reset --hard origin/master`
  2. `docker compose build --pull api frontend` (or `--no-cache` if `force_rebuild=true`)
  3. `docker compose up -d --remove-orphans` — rebuilds api + frontend containers; alembic migrations and admin seeding run inside the api container's CMD on startup
  4. `docker image prune -f` — clears dangling layers so the VPS disk doesn't fill up
  5. Post-deploy health check via `curl https://jobs.alisadikinma.com/api/health` (retries for 60s while the api container boots)

CI does **not** gate the deploy — they run in parallel. If you want CI-passing-required-before-deploy, switch the `on:` block in `deploy.yml` to `workflow_run` triggered by `ci.yml`.

## Required GitHub Secrets

Go to **Settings → Secrets and variables → Actions → New repository secret** and add (verified values for srv941303):

| Secret | Value | Purpose |
|---|---|---|
| `VPS_SSH_HOST` | `31.97.188.145` | srv941303 public IP (matches `.mcp.json`) |
| `VPS_SSH_USER` | `claudesn` | UID 1003, member of `sudo` + `www-data` (matches `.mcp.json`) |
| `VPS_SSH_KEY` | `-----BEGIN OPENSSH PRIVATE KEY-----\n...` | Private key (full contents). Use a dedicated deploy key (preferred) or `~/.ssh/id_ed25519` (the same key the local `.mcp.json` uses) |
| `VPS_SSH_PORT` | `22` (optional, default works) | Override only if SSH runs on a non-standard port |
| `VPS_PROJECT_PATH` | `/home/claudesn/jobhunter` | Where the repo will live on the VPS (claudesn owns home — no permission gymnastics) |

### Generating the SSH key (recommended — dedicated deploy key)

On your local machine:
```bash
ssh-keygen -t ed25519 -C "github-actions-jobhunter" -f ~/.ssh/jobhunter_deploy -N ""
cat ~/.ssh/jobhunter_deploy.pub    # → append to claudesn's ~/.ssh/authorized_keys on the VPS
cat ~/.ssh/jobhunter_deploy        # → paste full contents into the VPS_SSH_KEY secret
```

Append the public key on the VPS:
```bash
ssh claudesn@31.97.188.145
echo "<paste public key>" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

(Quicker alternative: reuse `~/.ssh/id_ed25519` from `.mcp.json` for `VPS_SSH_KEY`. Works but rotates that one key out of every project at once if it ever leaks. Dedicated key is cleaner.)

## First-run bootstrap on srv941303

One-time setup as `claudesn`. After this, every push to `master` deploys automatically.

```bash
ssh claudesn@31.97.188.145

# 1. Optional but recommended: add to docker group so deploy.sh doesn't need sudo.
#    Skip if you'd rather keep the script's `sudo docker` auto-fallback in play.
sudo usermod -aG docker $USER
newgrp docker
docker info >/dev/null && echo "docker socket OK" || echo "still need sudo"

# 2. Clone the repo
git clone https://github.com/alisadikinma/jobhunter.git ~/jobhunter
cd ~/jobhunter

# 3. Build the .env from .env.example (production values)
cp .env.example .env
# Edit .env — set:
#   ENV=prod
#   POSTGRES_PASSWORD=<generate>
#   JWT_SECRET=<python -c "import secrets; print(secrets.token_urlsafe(48))">
#   CALLBACK_SECRET=<python -c "import secrets; print(secrets.token_urlsafe(48))">
#   APIFY_FERNET_KEY=<python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
#   ADMIN_EMAIL / ADMIN_PASSWORD
#   MAIL_* (Hostinger creds — same as local .env)
#   POSTGRES_PASSWORD must match the password baked into DATABASE_URL

# 4. Smoke test the deploy script manually (verifies everything before letting CI fire)
bash scripts/deploy.sh

# 5. Confirm health
curl -sf https://jobs.alisadikinma.com/api/health
```

After step 5 returns `{"status":"ok"}`, configure the 5 GitHub secrets and the next `git push origin master` will auto-deploy.

## First-run checklist

- [ ] All 5 GitHub secrets configured (Settings → Secrets and variables → Actions)
- [ ] SSH from a workstation succeeds: `ssh claudesn@31.97.188.145 'whoami'`
- [ ] Repo cloned at `/home/claudesn/jobhunter`, `master` checked out
- [ ] `.env` filled in with production values (no defaults, no `change-me`)
- [ ] Either `docker info` runs cleanly as `claudesn` (preferred — added to docker group), OR passwordless `sudo` works (deploy.sh auto-detects)
- [ ] `docker compose version` shows v2.x (already verified: v2.39.2)
- [ ] Traefik is already running on the VPS (jobhunter compose only attaches via labels)
- [ ] DNS for `jobs.alisadikinma.com` points at `31.97.188.145`
- [ ] Smoke test: push a docs-only commit to `master`, watch the Actions tab

## Manual trigger + dispatch options

From the GitHub web UI → **Actions** → **Deploy to VPS** → **Run workflow**:

- **`force_rebuild`** (default `false`): runs `docker compose build --no-cache`. Use this **after the jobhunter-plugin repo has been updated** — the api Dockerfile clones the plugin during its build, and that layer is otherwise cached, so plugin updates won't flow through a normal deploy.
- **`skip_frontend`** (default `false`): skip rebuilding the Next.js image. Useful when you've only touched backend code and the frontend image is already current.

## Troubleshooting

**`Permission denied (publickey)`** — `VPS_SSH_KEY` doesn't match any entry in VPS `authorized_keys`. Re-check both files and that the public key was copied verbatim including the comment.

**`docker: permission denied while trying to connect to the Docker daemon socket`** — Deploy user is not in the `docker` group. Fix: `sudo usermod -aG docker <user>` then re-login (or `newgrp docker`).

**`docker compose: command not found` (v2 plugin missing)** — The script falls back to `docker-compose` (v1) automatically. Install one or the other on the VPS.

**Health check fails after 60s** — Check `docker compose logs api` on the VPS. Most common: alembic migration failed (look for `sqlalchemy.exc.*`), missing `.env` value crashed startup (look for pydantic `ValidationError`), or the api container is in `Restarting` state.

**Plugin skill changes not visible after deploy** — The `git clone` in `backend/Dockerfile` is cached by Docker. Either re-trigger the workflow with `force_rebuild=true`, or SSH in and run `docker compose build --no-cache api && docker compose up -d`.

**`alembic upgrade head: target database is not up to date`** — A migration crashed mid-apply previously. SSH in: `docker compose exec api alembic current` to inspect, then `docker compose exec api alembic upgrade head` manually.

**Two API workers fighting over the scheduler** — Should never happen (`--workers 1` is hard-coded in the Dockerfile CMD), but if it does, the symptom is duplicate scrape runs every 3 hours. Check `docker compose ps api` shows exactly one container.

## Concurrency

`concurrency: deploy-production` prevents two deploys from running simultaneously. `cancel-in-progress: false` means a push during an in-flight deploy queues the new one — it doesn't interrupt the active deploy mid-migration or mid-build.

## Stack quick reference

```
api          FastAPI + APScheduler + Claude CLI subprocess
frontend     Next.js 15 (App Router)
db           Postgres 16 (named volume `pgdata` — survives compose restarts)
redis        for Firecrawl (only spun up under --profile firecrawl)
firecrawl-*  optional, --profile firecrawl
```

Migrations: alembic, run automatically inside the api container's CMD on each `compose up`. Admin user: re-seeded idempotently from `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env`. Plugin: cloned from `github.com/alisadikinma/jobhunter-plugin` at api build time.
