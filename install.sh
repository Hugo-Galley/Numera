#!/usr/bin/env bash
# Installe Numera et le lance en production (docker-compose.prod.yml).
#
#   git clone https://github.com/Hugo-Galley/numera.git && cd numera && ./install.sh
# ou, sans cloner :
#   bash -c "$(curl -fsSL https://raw.githubusercontent.com/Hugo-Galley/numera/main/install.sh)"
#
# Relancer le script sur une installation existante garde le .env (et donc la clé des sauvegardes).

set -euo pipefail

REPO_URL="https://github.com/Hugo-Galley/numera.git"
COMPOSE_FILE="docker-compose.prod.yml"
APP_URL="http://localhost:8082"

if [ -t 1 ]; then
    BOLD=$'\033[1m'; GREEN=$'\033[0;32m'; RED=$'\033[0;31m'; DIM=$'\033[2m'; NC=$'\033[0m'
else
    BOLD=""; GREEN=""; RED=""; DIM=""; NC=""
fi

step() { printf '\n%s==> %s%s\n' "$BOLD" "$1" "$NC"; }
fail() { printf '%sErreur : %s%s\n' "$RED" "$1" "$NC" >&2; exit 1; }

# Les questions passent par le terminal, même quand le script est lu depuis curl.
ask() { local reply; read -r -p "$1" reply < /dev/tty; printf '%s' "$reply"; }
ask_secret() { local reply; read -r -s -p "$1" reply < /dev/tty; echo >&2; printf '%s' "$reply"; }

# --- Prérequis -----------------------------------------------------------------

step "Vérification des prérequis"
command -v git >/dev/null || fail "git n'est pas installé."
command -v openssl >/dev/null || fail "openssl n'est pas installé."
command -v curl >/dev/null || fail "curl n'est pas installé."
command -v docker >/dev/null || fail "Docker n'est pas installé (https://docs.docker.com/get-docker/)."
docker compose version >/dev/null 2>&1 || fail "le plugin Docker Compose est absent (commande 'docker compose')."
docker info >/dev/null 2>&1 || fail "impossible de joindre Docker. Le démon est-il lancé ? Votre utilisateur a-t-il accès à Docker (groupe docker ou sudo) ?"
echo "OK"

# --- Dépôt ---------------------------------------------------------------------

if [ ! -f "$COMPOSE_FILE" ] || [ ! -f "scripts/change_password.py" ]; then
    if [ -d numera/.git ]; then
        step "Mise à jour du dépôt existant dans ./numera"
        git -C numera pull --ff-only
    else
        step "Clonage du dépôt dans ./numera"
        git clone "$REPO_URL" numera
    fi
    cd numera
fi

# --- Configuration -------------------------------------------------------------

hash_password() {
    # bcrypt du mot de passe lu sur stdin : Python local si bcrypt y est installé, sinon un conteneur jetable.
    local script='import bcrypt, sys; print(bcrypt.hashpw(sys.stdin.read().encode(), bcrypt.gensalt()).decode())'
    if command -v python3 >/dev/null && python3 -c "import bcrypt" 2>/dev/null; then
        python3 -c "$script"
    else
        echo "${DIM}(bcrypt absent en local : calcul du hash dans un conteneur Python, ça peut prendre une minute)${NC}" >&2
        docker run --rm -i python:3.12-slim sh -c "pip install -q --disable-pip-version-check --root-user-action=ignore bcrypt >/dev/null && python -c '$script'"
    fi
}

write_env() {
    local username="$1" password_hash="$2" secret_key="$3" backup_key="$4"
    local line
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in
            ADMIN_USERNAME=*) printf 'ADMIN_USERNAME=%s\n' "$username" ;;
            # Guillemets simples : sinon Compose prend les $ du hash bcrypt pour des variables.
            ADMIN_PASSWORD_HASH=*) printf "ADMIN_PASSWORD_HASH='%s'\n" "$password_hash" ;;
            SECRET_KEY=*) printf 'SECRET_KEY=%s\n' "$secret_key" ;;
            BACKUP_KEY=*) printf 'BACKUP_KEY=%s\n' "$backup_key" ;;
            *) printf '%s\n' "$line" ;;
        esac
    done < .env.example > .env
    chmod 600 .env
}

configure=1
if [ -f .env ]; then
    step "Un fichier .env existe déjà"
    echo "Le garder conserve vos identifiants et la clé qui déchiffre vos sauvegardes."
    case "$(ask "Le remplacer par une nouvelle configuration ? [o/N] ")" in
        [oOyY]*) cp .env ".env.bak.$(date +%Y%m%d%H%M%S)"; echo "Ancien fichier sauvegardé en .env.bak.*" ;;
        *) configure=0 ;;
    esac
fi

if [ "$configure" -eq 1 ]; then
    step "Compte administrateur"
    username="$(ask "Identifiant [admin] : ")"
    username="${username:-admin}"
    [[ "$username" =~ ^[A-Za-z0-9._@-]+$ ]] || fail "identifiant invalide (lettres, chiffres, . _ @ - uniquement)."

    while true; do
        password="$(ask_secret "Mot de passe : ")"
        if [ "${#password}" -lt 8 ]; then echo "8 caractères minimum."; continue; fi
        confirm="$(ask_secret "Confirmation : ")"
        [ "$password" = "$confirm" ] && break
        echo "Les deux saisies ne correspondent pas, on recommence."
    done

    step "Génération des clés"
    password_hash="$(printf '%s' "$password" | hash_password)"
    unset password confirm
    [[ "$password_hash" == \$2* ]] || fail "le calcul du hash du mot de passe a échoué."
    secret_key="$(openssl rand -hex 32)"
    # Clé Fernet = 32 octets aléatoires en base64 « url-safe ».
    backup_key="$(openssl rand -base64 32 | tr '+/' '-_')"

    mkdir -p backend/data backups
    write_env "$username" "$password_hash" "$secret_key" "$backup_key"
    echo ".env créé."
fi

# --- Lancement -----------------------------------------------------------------

step "Construction et démarrage des conteneurs (quelques minutes la première fois)"
docker compose --env-file .env -f "$COMPOSE_FILE" up -d --build

step "Attente du démarrage de l'API"
for _ in $(seq 1 60); do
    if curl -fsS "$APP_URL/api/health" >/dev/null 2>&1; then
        printf '\n%sNumera tourne sur %s%s\n' "$GREEN" "$APP_URL" "$NC"
        if [ "$configure" -eq 1 ]; then
            echo "Connectez-vous avec l'identifiant « $username »."
            echo
            echo "Pensez à copier BACKUP_KEY (dans .env) en lieu sûr : sans elle, les sauvegardes sont illisibles."
        fi
        exit 0
    fi
    sleep 2
done

fail "l'application ne répond pas sur $APP_URL après 2 minutes. Regardez les logs : docker compose -f $COMPOSE_FILE logs backend"
