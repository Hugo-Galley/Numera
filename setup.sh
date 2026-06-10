#!/bin/bash

# setup.sh - Script d'initialisation pour Suivi Budget

set -e

echo "🚀 Initialisation de Suivi Budget..."

# 1. Copier le fichier .env si nécessaire
if [ ! -f .env ]; then
    echo "📄 Création du fichier .env à partir de .env.example..."
    cp .env.example .env
    echo "⚠️  N'oubliez pas d'éditer le fichier .env pour changer les clés et mots de passe !"
else
    echo "✅ Fichier .env déjà présent."
fi

# 2. Générer une SECRET_KEY si elle est par défaut
if grep -q "generate-a-long-random-key-here" .env; then
    echo "🔑 Génération d'une SECRET_KEY aléatoire..."
    NEW_KEY=$(openssl rand -hex 32)
    # Utilisation de sed pour remplacer la ligne
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/SECRET_KEY=generate-a-long-random-key-here/SECRET_KEY=$NEW_KEY/" .env
    else
        sed -i "s/SECRET_KEY=generate-a-long-random-key-here/SECRET_KEY=$NEW_KEY/" .env
    fi
fi

# 3. Générer une BACKUP_KEY si elle est par défaut
if grep -q "generate-a-fernet-key-using-python" .env; then
    echo "🛡️  Génération d'une BACKUP_KEY pour les sauvegardes chiffrées..."
    NEW_BACKUP_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || echo "")
    if [ -n "$NEW_BACKUP_KEY" ]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/BACKUP_KEY=generate-a-fernet-key-using-python/BACKUP_KEY=$NEW_BACKUP_KEY/" .env
        else
            sed -i "s/BACKUP_KEY=generate-a-fernet-key-using-python/BACKUP_KEY=$NEW_BACKUP_KEY/" .env
        fi
    else
        echo "❌ Échec de génération de la BACKUP_KEY (cryptography non installé ?). Vous devrez la générer manuellement."
    fi
fi

# 4. Créer les dossiers nécessaires
echo "📁 Création des dossiers de données et sauvegardes..."
mkdir -p backend/data
mkdir -p backups

echo ""
echo "✅ Configuration de base terminée !"
echo "👉 Prochaines étapes :"
echo "   1. Éditez le fichier .env pour définir votre ADMIN_PASSWORD_HASH"
echo "   2. Lancez l'application avec : make prod"
echo ""
