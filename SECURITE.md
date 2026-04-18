# Sécurité du projet Reconnaissance Faciale

## 1. Clés et secrets

- Toutes les clés (API, admin, etc.) doivent être stockées dans le fichier `.env` (jamais en dur dans le code).
- Ne jamais versionner `.env` (utiliser `.env.example` pour référence).

## 2. CORS et réseau

- Le backend n’accepte que les requêtes du frontend configuré (`FRONTEND_ORIGIN`).
- En production, lancer FastAPI sur `127.0.0.1` et placer un reverse proxy (nginx, traefik…) devant.
- Toujours utiliser HTTPS en production.

## 3. Authentification

- L’API admin est protégée par une clé forte (`FACE_ADMIN_API_KEY`).
- Pour une sécurité avancée, activer l’authentification utilisateur (voir ci-dessous).

## 4. Ports

- N’exposez que les ports nécessaires (8000 pour l’API, 5173 pour le dev frontend).
- Fermez les autres ports sur le firewall.

## 5. Utilisateurs (option JWT)

Pour activer l’authentification JWT :

1. Créez un utilisateur admin avec mot de passe.
2. Ajoutez un endpoint `/auth/login` qui retourne un JWT.
3. Protégez les routes sensibles avec un décorateur qui vérifie le JWT.

## 6. Mises à jour

- Gardez vos dépendances à jour (pip, npm).

## 7. Logs

- Ne logguez jamais de secrets ou de données sensibles.

---

Voir aussi AGENTS.md pour les règles de configuration et d’API.
