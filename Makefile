COMPOSE_FILE=infra/docker-compose.yml

# Interpréteur Python pour les tests : venv du backend si présent, sinon python3.12 / python3.11 du PATH
# (Python 3.14 est incompatible avec pydantic-core). Surchargeable : make test PYTHON=...
PYTHON ?= $(shell if [ -x $(CURDIR)/backend/venv/bin/python ]; then echo $(CURDIR)/backend/venv/bin/python; else command -v python3.12 || command -v python3.11; fi)

.PHONY: setup dev down prod prod-down demo demo-down backend-install frontend-install backend-seed-demo test test-front test-e2e lint lint-fix check-size validate backup-now backup-restore release-check release

setup:
	chmod +x setup.sh
	./setup.sh

dev:
	docker compose --env-file .env -f infra/docker-compose.yml up --build

down:
	docker compose --env-file .env -f infra/docker-compose.yml down

prod:
	docker compose --env-file .env -f docker-compose.prod.yml up -d --build

prod-down:
	docker compose --env-file .env -f docker-compose.prod.yml down

# Instance de démonstration publique (données fictives, base séparée, port 8090)
demo:
	docker compose --env-file .env -p numera-demo -f docker-compose.demo.yml up -d --build

demo-down:
	docker compose --env-file .env -p numera-demo -f docker-compose.demo.yml down

backend-install:
	python3 -m venv .venv && . .venv/bin/activate && pip install -r backend/requirements-dev.txt

frontend-install:
	cd frontend && npm install

# Régénère la démo en local dans backend/data/demo.db (jamais dans la vraie base, cf. DEMO_MODE)
backend-seed-demo:
	cd backend && DEMO_MODE=true DATABASE_URL=sqlite:///./data/demo.db PYTHONPATH=. $(PYTHON) scripts/seed_demo.py

test:
	cd backend && PYTHONPATH=. $(PYTHON) -m pytest tests/ -q

# Lint Python du backend (règles dans backend/ruff.toml) ; `make lint-fix` corrige ce qui est sûr
lint:
	cd backend && $(PYTHON) -m ruff check app tests scripts alembic

lint-fix:
	cd backend && $(PYTHON) -m ruff check app tests scripts alembic --fix

# Tests frontend (Vitest + Testing Library + MSW, cf. frontend/src/CLAUDE.md § Vérification)
test-front:
	cd frontend && npm test

# Tests E2E (Playwright : backend sur base de démo jetable + Vite, cf. frontend/e2e/README.md)
test-e2e:
	cd frontend && npm run test:e2e

frontend-build:
	cd frontend && npm run build

check-size:
	python3 scripts/check_code_size.py

validate: lint check-size test test-front frontend-build
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
	@echo "Bump suggéré : $$($(PYTHON) scripts/release_notes.py --bump) → v$$($(PYTHON) scripts/release_notes.py --next)"
	@$(PYTHON) scripts/release_notes.py --notes "v$$($(PYTHON) scripts/release_notes.py --next)"

release:
	@test -n "$(V)" || { echo "usage : make release V=X.Y.Z"; exit 1; }
	@echo "$(V)" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$$' || { echo "version invalide : $(V)"; exit 1; }
	@test "$$(git branch --show-current)" = main || { echo "il faut être sur main"; exit 1; }
	@test -z "$$(git status --porcelain)" || { echo "arbre de travail non propre"; exit 1; }
	@git fetch --tags --quiet && test "$$(git rev-parse HEAD)" = "$$(git rev-parse origin/main)" || { echo "main n'est pas synchronisé avec origin/main"; exit 1; }
	@! git rev-parse -q --verify refs/tags/v$(V) >/dev/null || { echo "le tag v$(V) existe déjà"; exit 1; }
	git tag -a v$(V) -m "Numera $(V)"
	git push origin v$(V)
