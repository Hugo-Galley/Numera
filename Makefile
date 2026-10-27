COMPOSE_FILE=infra/docker-compose.yml

# Interpréteur Python pour les tests : venv du backend si présent, sinon python3.12 / python3.11 du PATH
# (Python 3.14 est incompatible avec pydantic-core). Surchargeable : make test PYTHON=...
PYTHON ?= $(shell if [ -x $(CURDIR)/backend/venv/bin/python ]; then echo $(CURDIR)/backend/venv/bin/python; else command -v python3.12 || command -v python3.11; fi)

.PHONY: setup dev down prod prod-down demo demo-down backend-install frontend-install backend-seed-demo test validate backup-now backup-restore

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

# Instance de démonstration publique (données fictives, base séparée, port 8083)
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

frontend-build:
	cd frontend && npm run build

validate: test frontend-build
	@echo "Validation complete: Backend tests passed and Frontend builds successfully."

backup-now:
	docker exec suivi-budget-backup python scripts/backup.py

backup-restore:
	@echo "Usage: make backup-restore FILE=backups/suivi_budget_...db.enc"
	PYTHONPATH=backend python3 backend/scripts/restore.py $(FILE)

upgrade:
	make prod-down
	git pull origin main
	make prod

