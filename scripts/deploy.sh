#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# JobHunter VPS deploy script.
#
# Runs ON the VPS, in the project root. Designed to be:
#   - Idempotent (safe to re-run)
#   - Non-interactive (for CI/CD)
#   - Fail-fast (halts on any error, with clear diagnostic output)
#
# Stack is Docker-based: api + frontend + db + redis + (optional firecrawl)
# all run as compose services. Alembic migrations and admin seeding happen
# automatically inside the api container's CMD on startup, so this script
# only has to: git pull → rebuild images → recreate containers.
#
# Invocation:
#   ./scripts/deploy.sh                        # standard deploy (uses cache)
#   DEPLOY_FORCE_REBUILD=1 ./scripts/deploy.sh # --no-cache rebuild (use after
#                                                jobhunter-plugin repo updates,
#                                                or when Dockerfile-cached
#                                                git clone needs busting)
#   DEPLOY_SKIP_FRONTEND=1 ./scripts/deploy.sh # skip frontend rebuild
#
# Triggered by .github/workflows/deploy.yml on push to master.
# ------------------------------------------------------------------------------

set -euo pipefail

# ---- 0. Load shell environment (non-interactive SSH skips these by default) --
# Tools like docker often need PATH from login profiles; sourcing them is
# best-effort. Disable nounset temporarily — system rc files reference
# unset vars and would trip `set -u`.
set +u
[ -f /etc/profile ]          && . /etc/profile           || true
[ -f "$HOME/.bashrc" ]       && . "$HOME/.bashrc"        || true
[ -f "$HOME/.profile" ]      && . "$HOME/.profile"       || true
[ -f "$HOME/.bash_profile" ] && . "$HOME/.bash_profile"  || true
set -u

export PATH="$HOME/.local/bin:$HOME/bin:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin:$PATH"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "▶ Deploying jobhunter from $(pwd) @ $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
echo "▶ User: $(whoami) | Host: $(hostname)"

# ---- 0.5. Preflight: docker + compose available ------------------------------
echo "▶ Preflight tool check:"
missing_tools=()
for tool in git docker; do
  if path="$(command -v "$tool" 2>/dev/null)"; then
    printf "  ✓ %-10s %s\n" "$tool" "$path"
  else
    printf "  ✗ %-10s NOT FOUND\n" "$tool"
    missing_tools+=("$tool")
  fi
done

# Resolve compose CLI: prefer `docker compose` (v2 plugin), fall back to
# `docker-compose` (v1 standalone). Bail if neither.
if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
  printf "  ✓ %-10s docker compose (v2 plugin)\n" "compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE="docker-compose"
  printf "  ✓ %-10s %s\n" "compose" "$(command -v docker-compose)"
else
  printf "  ✗ %-10s NOT FOUND (need 'docker compose' v2 or 'docker-compose' v1)\n" "compose"
  missing_tools+=("compose")
fi

if [ ${#missing_tools[@]} -gt 0 ]; then
  echo ""
  echo "❌ Missing tools: ${missing_tools[*]}"
  echo "   Fix: ensure they're installed on the VPS and the deploy user is in the 'docker' group."
  echo "   Verify with:  docker info  (should print server info, not 'permission denied')"
  exit 127
fi

# ---- 1. Git sync -------------------------------------------------------------
echo "▶ git fetch + fast-forward origin/master"
git fetch origin master --quiet
git reset --hard origin/master
echo "  HEAD: $(git rev-parse --short HEAD) — $(git log -1 --pretty=format:%s)"

# ---- 2. .env sanity check ----------------------------------------------------
# docker-compose.yml uses `${VAR:?msg}` for required secrets, so missing values
# fail at compose-up time. Surface this early with a friendlier message.
if [ ! -f .env ]; then
  echo "❌ .env missing in $(pwd)"
  echo "   Copy .env.example to .env and fill in production values."
  exit 1
fi

# ---- 3. Build images ---------------------------------------------------------
# The api image clones jobhunter-plugin during its build (see backend/Dockerfile).
# Docker layer cache will reuse a previously cloned copy unless we bust it —
# set DEPLOY_FORCE_REBUILD=1 (e.g. after a plugin-only update) to force a clean
# rebuild.
build_targets=(api)
if [ "${DEPLOY_SKIP_FRONTEND:-0}" != "1" ]; then
  build_targets+=(frontend)
fi

if [ "${DEPLOY_FORCE_REBUILD:-0}" = "1" ]; then
  echo "▶ ${COMPOSE} build --no-cache --pull ${build_targets[*]}"
  $COMPOSE build --no-cache --pull "${build_targets[@]}"
else
  echo "▶ ${COMPOSE} build --pull ${build_targets[*]}"
  $COMPOSE build --pull "${build_targets[@]}"
fi

# ---- 4. Recreate containers --------------------------------------------------
# Compose only recreates services whose image/config changed. Volumes (pgdata,
# cv_storage) survive. The api container's CMD runs `alembic upgrade head` and
# `seed_admin.py` before uvicorn starts, so no separate migrate step here.
echo "▶ ${COMPOSE} up -d --remove-orphans"
$COMPOSE up -d --remove-orphans

# ---- 5. Cleanup --------------------------------------------------------------
# Prune dangling images so the VPS disk doesn't fill up. Volumes are preserved
# (no -a, no --volumes).
echo "▶ docker image prune -f"
docker image prune -f >/dev/null 2>&1 || true

echo ""
echo "✓ Deploy complete @ $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
echo "  HEAD: $(git rev-parse --short HEAD)"
echo "  Hint: post-deploy health check at https://jobs.alisadikinma.com/api/health"
