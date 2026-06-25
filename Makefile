COMPOSE_FILE=infra/docker-compose.yml

.PHONY: setup dev down prod prod-down backend-install frontend-install backend-seed-demo test validate backup-now backup-restore

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

backend-install:
	python3 -m venv .venv && . .venv/bin/activate && pip install -r backend/requirements.txt

frontend-install:
	cd frontend && npm install

backend-seed-demo:
	PYTHONPATH=backend python3 backend/scripts/seed_demo.py

test:
	cd backend && PYTHONPATH=. ./venv/bin/pytest tests/

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

