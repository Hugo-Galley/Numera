#!/bin/bash

# Budget Tracker Installer

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo "|____________________________________________________________________________|";
echo "|     ____            __           __     ______                __            |"
echo "|    / __ )__  ______/ /___ ____  / /_   /_  __/________ ______/ /_____  _____|"
echo "|   / __  / / / / __  / __ `/ _ \/ __/    / / / ___/ __ `/ ___/ //_/ _ \/ ___/|"
echo "|  / /_/ / /_/ / /_/ / /_/ /  __/ /_     / / / /  / /_/ / /__/ ,< /  __/ /    |"
echo "| /_____/\__,_/\__,_/\__, /\___/\__/    /_/ /_/   \__,_/\___/_/|_|\___/_/     |"
echo "|                   /____/                                                    |"
echo "|____________________________________________________________________________|";

# Check if we are inside the repo, if not clone it
if [ ! -f "scripts/change_password.py" ]; then
    echo -e "${BLUE}Clonage du dépôt Budget Tracker...${NC}"
    git clone https://github.com/Hugo-Galley/budget-tracker.git
    cd budget-tracker || exit 1
fi

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}   Budget Tracker — Installer${NC}"
echo -e "${BLUE}========================================${NC}\n"

# 1. Credentials
echo -e "${BLUE}[1/4] Configuration des accès admin${NC}"
read -p "Nom d'utilisateur admin [admin]: " ADMIN_USERNAME
ADMIN_USERNAME=${ADMIN_USERNAME:-admin}

read -s -p "Mot de passe admin: " ADMIN_PASSWORD
echo -e "\n"

if [ -z "$ADMIN_PASSWORD" ]; then
    echo -e "${RED}Erreur: Le mot de passe ne peut pas être vide.${NC}"
    exit 1
fi

# 2. Generation of Keys and Hash
echo -e "${GREEN}[2/4] Génération des clés de sécurité et du hash...${NC}"

# Password Hash
ADMIN_PASSWORD_HASH=$(python3 scripts/change_password.py "$ADMIN_PASSWORD" --raw)

# Secret Key
SECRET_KEY=$(openssl rand -hex 32)

# Backup Key (Fernet)
BACKUP_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || openssl rand -base64 32)

# 3. .env Configuration
echo -e "${GREEN}[3/4] Création du fichier .env...${NC}"

if [ ! -f ".env.example" ]; then
    echo -e "${RED}Erreur: .env.example non trouvé.${NC}"
    exit 1
fi

cp .env.example .env
mkdir -p backend/data backups

# Use Python for safe replacement in .env
export ADMIN_USERNAME ADMIN_PASSWORD ADMIN_PASSWORD_HASH SECRET_KEY BACKUP_KEY
python3 <<'EOF'
import os

env_path = '.env'
updates = {
    'ADMIN_USERNAME': os.environ.get('ADMIN_USERNAME'),
    'ADMIN_PASSWORD_HASH': os.environ.get('ADMIN_PASSWORD_HASH'),
    'MCP_API_PASSWORD': os.environ.get('ADMIN_PASSWORD'),
    'SECRET_KEY': os.environ.get('SECRET_KEY'),
    'BACKUP_KEY': os.environ.get('BACKUP_KEY')
}

with open(env_path, 'r') as f:
    lines = f.readlines()

with open(env_path, 'w') as f:
    for line in lines:
        updated = False
        for key, value in updates.items():
            if line.startswith(f"{key}="):
                f.write(f"{key}={value}\n")
                updated = True
                break
        if not updated:
            f.write(line)
EOF

# 4. Launching Production
echo -e "${GREEN}[4/4] Lancement des conteneurs (make prod)...${NC}"
make prod

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}== Installation terminée avec succès ! ==${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Utilisateur: ${BLUE}$ADMIN_USERNAME${NC}"
echo -e "Application: ${BLUE}http://localhost:8081${NC}"
echo -e "========================================\n"
