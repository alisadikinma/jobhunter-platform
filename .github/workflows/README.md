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

Go to **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret | Example value | Purpose |
|---|---|---|
| `VPS_SSH_HOST` | `jobs.alisadikinma.com` or `<srv941303 IP>` | VPS hostname or IP |
| `VPS_SSH_USER` | `deploy` | SSH user with project-directory write access AND membership in the `docker` group |
| `VPS_SSH_KEY` | `-----BEGIN OPENSSH PRIVATE KEY-----\n...` | Private key (full contents) — matches an `authorized_keys` entry on the VPS |
| `VPS_SSH_PORT` | `22` (optional) | Override if SSH runs on a non-standard port |
| `VPS_PROJECT_PATH` | `/srv/jobhunter` (or wherever you cloned this repo) | Absolute path to the project root on the VPS |

### Generating the SSH key

On your local machine:
```bash
ssh-keygen -t ed25519 -C "github-actions-jobhunter" -f ~/.ssh/jobhunter_deploy -N ""
cat ~/.ssh/jobhunter_deploy.pub    # add this line to VPS ~/.ssh/authorized_keys
cat ~/.ssh/jobhunter_deploy        # paste full contents into VPS_SSH_KEY secret
```

On the VPS (as the deploy user):
```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo "<paste public key here>" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

## First-run checklist on the VPS

- [ ] Repo is cloned at `VPS_PROJECT_PATH` and `master` is checked out
- [ ] `.env` exists in the repo root with all production values (see `.env.example` — `JWT_SECRET`, `CALLBACK_SECRET` ≥32 bytes, `APIFY_FERNET_KEY` generated, `POSTGRES_PASSWORD`, mailbox creds optional)
- [ ] Deploy user is in the `docker` group: `sudo usermod -aG docker $USER && newgrp docker`
- [ ] `docker info` runs cleanly as the deploy user (no `permission denied`)
- [ ] Either `docker compose version` (v2 plugin) OR `docker-compose --version` (v1) prints a version
- [ ] Traefik is already running on the VPS (jobhunter compose attaches via labels — it does not bring up Traefik itself)
- [ ] DNS for `jobs.alisadikinma.com` points at the VPS IP
- [ ] All 5 GitHub secrets configured
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
