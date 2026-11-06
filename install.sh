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
#
# Mise à jour (mode Docker) : ... install.sh)" _ --upgrade  (ou NUMERA_UPGRADE=1 bash -c "$(curl …)"). Le compose publié fixe la version
# des images : `docker compose pull && up -d` seul ne change donc PAS de version. --upgrade retélécharge le
# compose de la dernière release (ou de NUMERA_VERSION=x.y.z), le vérifie (SHA256SUMS), sauvegarde la base,
# puis tire les images et redémarre. La base est aussi sauvegardée au démarrage si le schéma doit changer.

set -euo pipefail

REPO_URL="https://github.com/Hugo-Galley/numera.git"
RELEASES_URL="https://github.com/Hugo-Galley/numera/releases"
APP_URL="http://localhost:8082"
# Image jetable pour hacher le mot de passe : épinglée par digest (comme backend/Dockerfile), bcrypt par version + hashes
HASH_IMAGE="python:3.12-slim@sha256:e695ab189fa2d082b1c61c69a6b888a5adeca61ceeccad107b1ed2a125721a9e"
BCRYPT_REQUIREMENTS='bcrypt==5.0.0 \
    --hash=sha256:c2388ca94ffee269b6038d48747f4ce8df0ffbea43f31abfa18ac72f0218effb \
    --hash=sha256:560ddb6ec730386e7b3b26b8b4c88197aaed924430e7b74666a586ac997249ef \
    --hash=sha256:d79e5c65dcc9af213594d6f7f1fa2c98ad3fc10431e7aa53c176b441943efbdd \
    --hash=sha256:0c8e093ea2532601a6f686edbc2c6b2ec24131ff5c52f7610dd64fa4553b5464 \
    --hash=sha256:5b1589f4839a0899c146e8892efe320c0fa096568abd9b95593efac50a87cb75 \
    --hash=sha256:89042e61b5e808b67daf24a434d89bab164d4de1746b37a8d173b6b14f3db9ff \
    --hash=sha256:e3cf5b2560c7b5a142286f69bde914494b6d8f901aaa71e453078388a50881c4 \
    --hash=sha256:f632fd56fc4e61564f78b46a2269153122db34988e78b6be8b32d28507b7eaeb \
    --hash=sha256:801cad5ccb6b87d1b430f183269b94c24f248dddbbc5c1f78b6ed231743e001c \
    --hash=sha256:3cf67a804fc66fc217e6914a5635000259fbbbb12e78a99488e4d5ba445a71eb \
    --hash=sha256:ddb4e1500f6efdd402218ffe34d040a1196c072e07929b9820f363a1fd1f4191 \
    --hash=sha256:7aeef54b60ceddb6f30ee3db090351ecf0d40ec6e2abf41430997407a46d2254 \
    --hash=sha256:f0ce778135f60799d89c9693b9b398819d15f1921ba15fe719acb3178215a7db \
    --hash=sha256:f8429e1c410b4073944f03bd778a9e066e7fad723564a52ff91841d278dfc822 \
    --hash=sha256:edfcdcedd0d0f05850c52ba3127b1fce70b9f89e0fe5ff16517df7e81fa3cbb8 \
    --hash=sha256:611f0a17aa4a25a69362dcc299fda5c8a3d4f160e2abb3831041feb77393a14a \
    --hash=sha256:db99dca3b1fdc3db87d7c57eac0c82281242d1eabf19dcb8a6b10eb29a2e72d1 \
    --hash=sha256:5feebf85a9cefda32966d8171f5db7e3ba964b77fdfe31919622256f80f9cf42 \
    --hash=sha256:3ca8a166b1140436e058298a34d88032ab62f15aae1c598580333dc21d27ef10 \
    --hash=sha256:61afc381250c3182d9078551e3ac3a41da14154fbff647ddf52a769f588c4172'

upgrade=0
for arg in "$@"; do
    case "$arg" in
        --upgrade) upgrade=1 ;;
        -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
        *) printf 'Option inconnue : %s\n' "$arg" >&2; exit 1 ;;
    esac
done
[ "${NUMERA_UPGRADE:-0}" = 1 ] && upgrade=1

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

sha256_of() {
    if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi
}

# --- Mode ----------------------------------------------------------------------

mode="${NUMERA_MODE:-}"
[ "$upgrade" -eq 1 ] && mode="${mode:-docker}"
if [ -z "$mode" ]; then
    if [ -f infra/docker-compose.prod.yml ] && [ -f scripts/ops/change_password.py ]; then
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
[ "$upgrade" -eq 1 ] && [ "$mode" = source ] && fail "--upgrade concerne le mode Docker ; depuis les sources : make upgrade."

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
    if [ ! -f "$COMPOSE_FILE" ] || [ ! -f "scripts/ops/change_password.py" ]; then
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
    # Lancé depuis le dossier d'installation (docker-compose.yml + .env présents) : on y reste
    if [ ! -f "$COMPOSE_FILE" ] || [ ! -f .env ]; then
        mkdir -p numera
        cd numera
    fi
    if [ "$upgrade" -eq 1 ]; then
        { [ -f .env ] && [ -f "$COMPOSE_FILE" ]; } || fail "aucune installation à mettre à jour (docker-compose.yml et .env introuvables dans $(pwd))."
        step "Mise à jour : sauvegarde de la base"
        if docker ps --format '{{.Names}}' | grep -qx numera-backup-prod; then
            docker exec numera-backup-prod python scripts/backup.py || echo "${RED}Sauvegarde impossible : poursuite (une copie est aussi faite avant toute migration).${NC}" >&2
        else
            echo "Conteneur de sauvegarde arrêté : ignoré (copie faite au démarrage si le schéma change)."
        fi
    fi
    step "Téléchargement de la configuration Docker"
    if [ -n "${NUMERA_VERSION:-}" ]; then
        release_url="$RELEASES_URL/download/v${NUMERA_VERSION#v}"
    else
        release_url="$RELEASES_URL/latest/download"
    fi
    curl -fsSL "$release_url/docker-compose.yml" -o "$COMPOSE_FILE.new" || { rm -f "$COMPOSE_FILE.new"; fail "impossible de télécharger $release_url/docker-compose.yml (aucune release publiée avec ce compose ?)."; }
    # Somme de contrôle publiée avec la release (absente des toutes premières versions : avertissement)
    if curl -fsSL "$release_url/SHA256SUMS" -o "$COMPOSE_FILE.sums"; then
        expected="$(awk '$2 == "docker-compose.yml" || $2 == "*docker-compose.yml" { print $1 }' "$COMPOSE_FILE.sums")"
        actual="$(sha256_of "$COMPOSE_FILE.new")"
        rm -f "$COMPOSE_FILE.sums"
        if [ -z "$expected" ] || [ "$expected" != "$actual" ]; then
            rm -f "$COMPOSE_FILE.new"
            fail "la somme de contrôle de docker-compose.yml ne correspond pas à SHA256SUMS : téléchargement abandonné."
        fi
        echo "Somme de contrôle SHA-256 vérifiée."
    else
        rm -f "$COMPOSE_FILE.sums"
        echo "${DIM}Pas de SHA256SUMS pour cette release : compose non vérifié.${NC}" >&2
    fi
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
        docker run --rm -i -e BCRYPT_REQUIREMENTS="$BCRYPT_REQUIREMENTS" "$HASH_IMAGE" sh -c "printf '%s\n' \"\$BCRYPT_REQUIREMENTS\" > /tmp/requirements.txt && pip install -q --disable-pip-version-check --root-user-action=ignore --require-hashes -r /tmp/requirements.txt >/dev/null && python -c '$script'"
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
BACKUP_INTERVAL_SECONDS=86400
# Envoi des sauvegardes chiffrées vers un dépôt GitHub PRIVÉ dédié (laisser vide = désactivé)
GITHUB_BACKUP_REPO=
GITHUB_BACKUP_TOKEN=
GITHUB_BACKUP_KEEP_DAYS=30
NUMERA_UID=1000
NUMERA_GID=1000
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
            # Les conteneurs backend (non-root) écrivent dans ./data et ./backups avec l'UID de l'utilisateur courant
            NUMERA_UID=*) printf 'NUMERA_UID=%s\n' "$(id -u)" ;;
            NUMERA_GID=*) printf 'NUMERA_GID=%s\n' "$(id -g)" ;;
            *) printf '%s\n' "$line" ;;
        esac
    done < <(env_template) > .env
    chmod 600 .env
}

configure=1
if [ "$upgrade" -eq 1 ]; then
    configure=0
elif [ -f .env ]; then
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
            echo "Mettre à jour plus tard : relancez la commande d'installation avec --upgrade (retélécharge le compose de la dernière release,"
            echo "sauvegarde la base, tire les images). Un simple « docker compose pull » ne change pas de version :"
            echo "la version est fixée dans docker-compose.yml. Version précise : NUMERA_VERSION=x.y.z."
        fi
        exit 0
    fi
    sleep 2
done

fail "l'application ne répond pas sur $APP_URL après 2 minutes. Regardez les logs : docker compose -f $COMPOSE_FILE logs backend"
