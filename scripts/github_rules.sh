#!/usr/bin/env bash
# Applique les réglages du dépôt GitHub (merge en squash, branches supprimées après merge) et les
# rulesets de .github/rulesets/*.json. Idempotent : crée ou met à jour chaque ruleset par son nom.
# Prérequis : gh authentifié avec les droits admin du dépôt.
#   scripts/github_rules.sh           # applique
#   scripts/github_rules.sh --dry-run # affiche ce qui serait fait
set -euo pipefail
cd "$(dirname "$0")/.."

dry=false
[ "${1:-}" = "--dry-run" ] && dry=true
repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
echo "Dépôt : $repo"

if $dry; then
  echo "[dry-run] réglages : squash seul, titre = titre de PR, suppression auto des branches, auto-merge autorisé"
else
  gh api -X PATCH "repos/$repo" \
    -F allow_squash_merge=true -F allow_merge_commit=false -F allow_rebase_merge=false \
    -f squash_merge_commit_title=PR_TITLE -f squash_merge_commit_message=BLANK \
    -F delete_branch_on_merge=true -F allow_auto_merge=true -F allow_update_branch=true >/dev/null
  echo "Réglages du dépôt appliqués"
fi

for file in .github/rulesets/*.json; do
  name=$(jq -r .name "$file")
  id=$(gh api "repos/$repo/rulesets" --jq ".[] | select(.name == \"$name\") | .id")
  if $dry; then
    echo "[dry-run] ruleset « $name » : ${id:+mise à jour #$id}${id:-création}"
  elif [ -n "$id" ]; then
    gh api -X PUT "repos/$repo/rulesets/$id" --input "$file" >/dev/null
    echo "Ruleset « $name » mis à jour (#$id)"
  else
    gh api -X POST "repos/$repo/rulesets" --input "$file" >/dev/null
    echo "Ruleset « $name » créé"
  fi
done
