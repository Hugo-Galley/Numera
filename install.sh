#!/usr/bin/env bash
# Installe Numera et le lance en production (infra/docker-compose.prod.yml).
#
#   bash -c "$(curl -fsSL https://raw.githubusercontent.com/Hugo-Galley/numera/main/install.sh)"
# ou, depuis un clone :
#   git clone https://github.com/Hugo-Galley/numera.git && cd numera && ./install.sh
#
# Deux modes (NUMERA_MODE=docker|source pour ne pas être interrogé) :
#   docker : images publiées de la dernière release (ou NUMERA_VERSION=x.y.z), rien à construire ;
#            l'installation vit dans ./numera (docker-compose.yml, .env, data/, backups/).
#   source : clone du dépôt et construction locale (infra/docker-compose.prod.yml).
#
# Relancer le script sur une installation existante garde le .env (et donc la clé des sauvegardes).

set -euo pipefail

REPO_URL="https://github.com/Hugo-Galley/numera.git"
RELEASES_URL="https://github.com/Hugo-Galley/numera/releases"
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

# --- Mode ----------------------------------------------------------------------

mode="${NUMERA_MODE:-}"
if [ -z "$mode" ]; then
    if [ -f infra/docker-compose.prod.yml ] && [ -f scripts/change_password.py ]; then
        mode=source   # lancé depuis un clone : on y reste
    else
        step "Mode d'installation"
        echo "  1) Docker       images prêtes à l'emploi, rien à construire, mises à jour en une commande (recommandé)"
        echo "  2) Depuis les sources   clone du dépôt et construction locale (pour modifier le code)"
        case "$(ask "Votre choix [1] : ")" in
            2) mode=source ;;
            *) mode=docker ;;
        esac
    fi
fi
case "$mode" in docker|source) ;; *) fail "NUMERA_MODE doit valoir « docker » ou « source »." ;; esac

# --- Prérequis -----------------------------------------------------------------

step "Vérification des prérequis"
[ "$mode" = source ] && { command -v git >/dev/null || fail "git n'est pas installé."; }
command -v openssl >/dev/null || fail "openssl n'est pas installé."
command -v curl >/dev/null || fail "curl n'est pas installé."
command -v docker >/dev/null || fail "Docker n'est pas installé (https://docs.docker.com/get-docker/)."
docker compose version >/dev/null 2>&1 || fail "le plugin Docker Compose est absent (commande 'docker compose')."
docker info >/dev/null 2>&1 || fail "impossible de joindre Docker. Le démon est-il lancé ? Votre utilisateur a-t-il accès à Docker (groupe docker ou sudo) ?"
echo "OK"

# --- Dossier d'installation ----------------------------------------------------

if [ "$mode" = source ]; then
    COMPOSE_FILE="infra/docker-compose.prod.yml"
    DATA_DIR="backend/data"
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
else
    COMPOSE_FILE="docker-compose.yml"
    DATA_DIR="data"
    mkdir -p numera
    cd numera
    step "Téléchargement de la configuration Docker"
    if [ -n "${NUMERA_VERSION:-}" ]; then
        compose_url="$RELEASES_URL/download/v${NUMERA_VERSION#v}/docker-compose.yml"
    else
        compose_url="$RELEASES_URL/latest/download/docker-compose.yml"
    fi
    curl -fsSL "$compose_url" -o "$COMPOSE_FILE.new" || { rm -f "$COMPOSE_FILE.new"; fail "impossible de télécharger $compose_url (aucune release publiée avec ce compose ?)."; }
    mv "$COMPOSE_FILE.new" "$COMPOSE_FILE"
    grep -m1 "NUMERA_VERSION:-" "$COMPOSE_FILE" | sed 's/.*NUMERA_VERSION:-\([^}]*\)}.*/Version : \1/'
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

# Mode source : .env.example du dépôt ; mode Docker : gabarit minimal (rien d'autre n'est cloné).
env_template() {
    if [ -f .env.example ]; then
        cat .env.example
    else
        cat <<'TEMPLATE'
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=
SECRET_KEY=
CORS_ORIGINS=http://localhost:8082
BACKUP_KEY=
RETENTION_DAYS=7
# Envoi des sauvegardes chiffrées vers un dépôt GitHub PRIVÉ dédié (laisser vide = désactivé)
GITHUB_BACKUP_REPO=
GITHUB_BACKUP_TOKEN=
TEMPLATE
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
    done < <(env_template) > .env
    # Les conteneurs backend écrivent dans ./data et ./backups avec l'UID de l'utilisateur courant (non-root)
    printf 'NUMERA_UID=%s\nNUMERA_GID=%s\n' "$(id -u)" "$(id -g)" >> .env
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

    mkdir -p "$DATA_DIR" backups
    write_env "$username" "$password_hash" "$secret_key" "$backup_key"
    echo ".env créé."
fi

# --- Lancement -----------------------------------------------------------------

if [ "$mode" = docker ]; then
    step "Téléchargement des images et démarrage"
    docker compose --env-file .env -f "$COMPOSE_FILE" pull
    docker compose --env-file .env -f "$COMPOSE_FILE" up -d --no-build
else
    step "Construction et démarrage des conteneurs (quelques minutes la première fois)"
    docker compose --env-file .env -f "$COMPOSE_FILE" up -d --build
fi

step "Attente du démarrage de l'API"
for _ in $(seq 1 60); do
    if curl -fsS "$APP_URL/api/health" >/dev/null 2>&1; then
        printf '\n%sNumera tourne sur %s%s\n' "$GREEN" "$APP_URL" "$NC"
        if [ "$configure" -eq 1 ]; then
            echo "Connectez-vous avec l'identifiant « $username »."
            echo
            echo "Pensez à copier BACKUP_KEY (dans .env) en lieu sûr : sans elle, les sauvegardes sont illisibles."
        fi
        if [ "$mode" = docker ]; then
            echo
            echo "Mettre à jour plus tard : relancez ce script (la configuration est conservée), ou"
            echo "  cd numera && docker compose --env-file .env pull && docker compose --env-file .env up -d"
        fi
        exit 0
    fi
    sleep 2
done

fail "l'application ne répond pas sur $APP_URL après 2 minutes. Regardez les logs : docker compose -f $COMPOSE_FILE logs backend"
