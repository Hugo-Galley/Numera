import bcrypt
import sys
import os

def generate_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 change_password.py <new_password> [--raw]")
        sys.exit(1)
    
    new_password = sys.argv[1]
    is_raw = "--raw" in sys.argv
    
    new_hash = generate_hash(new_password)
    
    if is_raw:
        sys.stdout.write(new_hash)
        sys.exit(0)
    
    # Escape for Docker Compose
    escaped_hash = new_hash.replace('$', '$$')
    
    print(f"\nNouveau mot de passe : {new_password}")
    print(f"Nouveau hash : {new_hash}")
    print("\n--- ÉTAPES POUR APPLIQUER ---")
    print("1. Ouvre le fichier '.env' à la racine du projet")
    print("2. Trouve la ligne 'ADMIN_PASSWORD_HASH'")
    print(f"3. Remplace la valeur par : {new_hash}")
    print("\nNote: Si vous utilisez Docker Compose directement dans le YAML (déconseillé), utilisez ce hash échappé :")
    print(f"ADMIN_PASSWORD_HASH={escaped_hash}")
    print("\n4. Relancez l'application : make dev (ou make prod)")
