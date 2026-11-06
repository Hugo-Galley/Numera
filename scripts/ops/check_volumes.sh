#!/usr/bin/env bash
# Prépare les dossiers montés dans les conteneurs backend (non-root, UID NUMERA_UID de .env) : les crée
# s'ils manquent (sinon Docker les crée en root) et refuse de lancer si un fichier n'appartient pas à
# cet UID, ce qui casse les sauvegardes (« unable to open database file ») et l'envoi de logos.
# Typiquement des fichiers écrits en root par une ancienne version des conteneurs.
#   scripts/ops/check_volumes.sh backend/data backups
set -euo pipefail
cd "$(dirname "$0")/../.."

uid=$(sed -n 's/^NUMERA_UID=//p' .env 2>/dev/null | tail -1)
gid=$(sed -n 's/^NUMERA_GID=//p' .env 2>/dev/null | tail -1)
uid=${uid:-1000}
gid=${gid:-1000}

bad=()
for dir in "$@"; do
  mkdir -p "$dir"
  if [ -n "$(find "$dir" ! -uid "$uid" -print -quit)" ]; then
    bad+=("$dir")
  fi
done

if [ ${#bad[@]} -gt 0 ]; then
  echo "❌ Fichiers n'appartenant pas à l'UID $uid (NUMERA_UID) dans : ${bad[*]}" >&2
  echo "   Les conteneurs ne pourront pas y écrire. Corrigez avec :" >&2
  echo "   sudo chown -R $uid:$gid ${bad[*]}" >&2
  exit 1
fi
