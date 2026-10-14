#!/usr/bin/env bash
# macOS / Linux setup. Run from the project root: bash scripts/setup.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
if [ ! -f .env ]; then
  cp .env.example .env
  SECRET=$(.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(48))")
  sed -i.bak "s|^JWT_SECRET=.*|JWT_SECRET=$SECRET|" .env && rm -f .env.bak
fi
.venv/bin/alembic upgrade head
.venv/bin/python -m scripts.seed_demo
cd "$ROOT/frontend" && npm ci
echo "Done. Backend: cd backend && .venv/bin/uvicorn app.main:app --reload | Frontend: cd frontend && npm run dev"
