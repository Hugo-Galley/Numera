COMPOSE_FILE=infra/docker-compose.yml

# Interpréteur Python pour les tests : backend/.venv (créé par `make backend-install`, uv), sinon l'ancien
# backend/venv, sinon python3.12 / python3.11 du PATH (Python 3.14 est incompatible avec pydantic-core).
# Surchargeable : make test PYTHON=...
PYTHON ?= $(shell for p in $(CURDIR)/backend/.venv/bin/python $(CURDIR)/backend/venv/bin/python; do if [ -x $$p ]; then echo $$p; exit; fi; done; command -v python3.12 || command -v python3.11)

.PHONY: setup dev down prod prod-down demo demo-down backend-install frontend-install backend-seed-demo test test-mcp coverage test-front test-e2e lint lint-fix lint-front typecheck check-size validate hooks pre-commit-all api-contract backup-now backup-restore release-check release dead-code knip

setup:
	chmod +x setup.sh
	./setup.sh

dev:
	scripts/ops/check_volumes.sh backend/data backups
	docker compose --env-file .env -f infra/docker-compose.yml up --build

down:
	docker compose --env-file .env -f infra/docker-compose.yml down

prod:
	scripts/ops/check_volumes.sh backend/data backups
	docker compose --env-file .env -f docker-compose.prod.yml up -d --build

prod-down:
	docker compose --env-file .env -f docker-compose.prod.yml down

# Instance de démonstration publique (données fictives, base séparée, port 8090)
demo:
	scripts/ops/check_volumes.sh backend/data-demo
	docker compose --env-file .env -p numera-demo -f docker-compose.demo.yml up -d --build

demo-down:
	docker compose --env-file .env -p numera-demo -f docker-compose.demo.yml down

backend-install:
	cd backend && uv sync --frozen

frontend-install:
	cd frontend && npm install

# Régénère la démo en local dans backend/data/demo.db (jamais dans la vraie base, cf. DEMO_MODE)
backend-seed-demo:
	cd backend && DEMO_MODE=true DATABASE_URL=sqlite:///./data/demo.db PYTHONPATH=. $(PYTHON) scripts/seed_demo.py

test:
	cd backend && PYTHONPATH=. $(PYTHON) -m pytest tests/ -q -n auto

# Tests du serveur MCP (surface figée, auth, lecture seule)
test-mcp:
	cd mcp-server && uv run --with pytest python -m pytest tests -q

# Tests + couverture avec seuil à cliquet : backend (backend/.coveragerc) puis frontend (frontend/vitest.config.ts)
coverage:
	cd backend && PYTHONPATH=. $(PYTHON) -m pytest tests/ -q -n auto --cov --cov-report=term:skip-covered
	cd frontend && npm run coverage

# Lint Python du backend (règles dans backend/ruff.toml) ; `make lint-fix` corrige ce qui est sûr
lint:
	cd backend && $(PYTHON) -m ruff check app tests scripts alembic
	cd mcp-server && uv run --with ruff ruff check .

lint-fix:
	cd backend && $(PYTHON) -m ruff check app tests scripts alembic --fix
	cd mcp-server && uv run --with ruff ruff check . --fix

# Lint frontend (ESLint, frontend/eslint.config.js) : erreurs bloquantes, avertissements plafonnés par frontend/eslint-baseline.json
lint-front:
	cd frontend && npm run lint

# Types Python (mypy, backend/mypy.ini) : strict sur app/domain et app/core, baseline à cliquet ailleurs (scripts/quality/baselines/mypy_baseline.json)
typecheck:
	PYTHON=$(PYTHON) $(PYTHON) scripts/quality/check_types.py

# Tests frontend (Vitest + Testing Library + MSW, cf. frontend/src/CLAUDE.md § Vérification)
test-front:
	cd frontend && npm test

# Tests E2E (Playwright : backend sur base de démo jetable + Vite, cf. frontend/e2e/README.md)
test-e2e:
	cd frontend && npm run test:e2e

frontend-build:
	cd frontend && npm run build

check-size:
	python3 scripts/quality/check_code_size.py

# Garde-fous locaux avant commit / push (.pre-commit-config.yaml) ; `pre-commit` s'installe avec `brew install pre-commit` ou `uv tool install pre-commit`
hooks:
	pre-commit install

pre-commit-all:
	pre-commit run --all-files

# Contrat API : exporte le schéma OpenAPI du backend puis régénère les types TypeScript (à commiter avec toute route/schéma modifié)
api-contract:
	cd backend && PYTHONPATH=. $(PYTHON) scripts/export_openapi.py
	cd frontend && npm run api:types

# Code mort backend (vulture, scripts/quality/check_dead_code.py) : fonctions, classes, méthodes et imports inutilisés ; faux positifs déclarés dans scripts/quality/baselines/dead_code_allowlist.json
dead-code:
	PYTHON=$(PYTHON) $(PYTHON) scripts/quality/check_dead_code.py

# Code mort frontend (knip, frontend/knip.json) : fichiers, dépendances, exports et types inutilisés
knip:
	cd frontend && npm run knip

validate: lint lint-front knip typecheck check-size dead-code test-mcp coverage frontend-build
	@echo "Validation complete: Backend and Frontend tests passed, Frontend builds successfully."

backup-now:
	docker exec suivi-budget-backup python scripts/backup.py

backup-restore:
	@echo "Usage: make backup-restore FILE=backups/suivi_budget_...db.enc"
	PYTHONPATH=backend python3 backend/scripts/restore.py $(FILE)

upgrade:
	make prod-down
	git pull origin main
	make prod


# Releases (cf. skill numera-release) : tag vX.Y.Z sur main, le workflow release.yml publie images et notes
release-check:
	@git fetch --tags --quiet
	@echo "Bump suggéré : $$($(PYTHON) scripts/release/release_notes.py --bump) → v$$($(PYTHON) scripts/release/release_notes.py --next)"
	@$(PYTHON) scripts/release/release_notes.py --notes "v$$($(PYTHON) scripts/release/release_notes.py --next)"

release:
	@test -n "$(V)" || { echo "usage : make release V=X.Y.Z"; exit 1; }
	@echo "$(V)" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$$' || { echo "version invalide : $(V)"; exit 1; }
	@case "$$(git branch --show-current)" in main|release/*) ;; *) echo "il faut être sur main ou release/X.Y"; exit 1;; esac
	@test -z "$$(git status --porcelain)" || { echo "arbre de travail non propre"; exit 1; }
	@git fetch --tags --quiet && test "$$(git rev-parse HEAD)" = "$$(git rev-parse origin/$$(git branch --show-current))" || { echo "la branche n'est pas synchronisée avec son origin"; exit 1; }
	@! git rev-parse -q --verify refs/tags/v$(V) >/dev/null || { echo "le tag v$(V) existe déjà"; exit 1; }
	git tag -a v$(V) -m "Numera $(V)"
	git push origin v$(V)
