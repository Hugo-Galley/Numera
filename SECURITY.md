# Politique de sécurité

## Signaler une vulnérabilité

Merci de **ne pas ouvrir d'issue publique**. Utilise le signalement privé de GitHub : onglet **Security** du dépôt → **Report a vulnerability** (<https://github.com/Hugo-Galley/Numera/security/advisories/new>).

Indique la version (ou le commit), les étapes pour reproduire et l'impact que tu estimes. Numera est un projet personnel maintenu sur le temps libre : attends un premier retour sous une semaine, sans engagement de délai de correction.

## Versions supportées

Seule la **dernière version publiée** reçoit des correctifs de sécurité (voir les [releases](https://github.com/Hugo-Galley/Numera/releases)). Une branche `release/X.Y` n'est ouverte que pour un correctif critique sur une version plus ancienne.

## Périmètre

Numera est une application **self-hostée, mono-utilisateur**, destinée à tourner derrière ton propre réseau ou un reverse proxy. Sont dans le périmètre : authentification (JWT, TOTP, passkeys), jetons MCP (lecture seule), import de fichiers, chiffrement des sauvegardes, images Docker. L'instance de démo publique ne contient que des données fictives.

## Ce qui est en place

Images non-root en lecture seule, dépendances et images scannées par Trivy à chaque PR et chaque semaine, images publiées signées (cosign) avec SBOM, actions GitHub et images de base épinglées par SHA / digest, secrets en variables d'environnement validées au démarrage en production.
