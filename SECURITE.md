# Securite du projet Reconnaissance Faciale

## 1. Secrets obligatoires

Variables requises par le backend:

- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `JWT_SECRET`
- `FACE_CONFIG_SECRET`
- `FACE_API_KEY`

Variables optionnelles:

- `JWT_EXPIRE_MINUTES` (`60` par defaut)
- `FRONTEND_ORIGINS` (liste separee par virgules)
- `FRONTEND_ORIGIN` (compatibilite legacy)

Regles:

- stocker les secrets hors du code source
- ne jamais versionner les fichiers contenant les secrets
- utiliser des valeurs longues, uniques et aleatoires
- ne pas reutiliser la meme valeur pour `JWT_SECRET`, `FACE_CONFIG_SECRET` et `FACE_API_KEY`

## 2. Auth admin

L'auth admin est active dans le projet actuel.

Comportement:

- `POST /api/auth/login` verifie `ADMIN_USERNAME` et `ADMIN_PASSWORD`
- le backend emet un JWT signe par `JWT_SECRET`
- la session est stockee dans le cookie HTTP-only `face_access_token`
- l'expiration est controlee par `JWT_EXPIRE_MINUTES`

Routes protegees:

- `/api/config`
- `/api/faces`
- `/api/faces/enroll`
- `/api/recognition/*`
- `/api/cameras/*`
- `/api/admin/batch-logs`

## 3. Chiffrement des secrets applicatifs

- les secrets de configuration stockes en base sont chiffres via `Fernet`
- la cle derive de `FACE_CONFIG_SECRET`
- si `FACE_CONFIG_SECRET` est absente, le backend ne peut pas chiffrer/dechiffrer ces valeurs

## 4. API production

L'API batch de production est separee de l'auth admin.

Regles:

- endpoint concerne: `POST /api/production/recognition/analyze-images`
- header requis: `x-api-key`
- la valeur attendue est `FACE_API_KEY`
- si `FACE_API_KEY` n'est pas definie, l'endpoint repond `503`

Rate limiting:

- la limite est configurable dans l'application
- `production_api_rate_limit_window_seconds` par defaut `60`
- `production_api_rate_limit_max_requests` par defaut `30`
- en depassement, l'API repond `429` avec `Retry-After`

## 5. CORS et exposition reseau

- configurer `FRONTEND_ORIGINS` avec uniquement les origines front autorisees
- en production, lancer FastAPI sur `127.0.0.1`
- placer un reverse proxy devant si exposition externe necessaire
- utiliser HTTPS en production

## 6. Ports et surface d'exposition

- n'exposer que les ports necessaires
- en dev, le frontend Vite utilise generalement `5173`
- le backend local utilise generalement `8001`
- fermer les autres ports au niveau firewall ou reverse proxy

## 7. Logs et donnees sensibles

- ne jamais logguer de secrets
- ne pas exposer les embeddings faciaux via l'API
- ne pas rendre de HTML brut issu des donnees utilisateur

## 8. Hygiene operationnelle

- garder les dependances Python et npm a jour
- utiliser `backend/requirements.txt` pour le runtime
- utiliser `backend/requirements-dev.txt` uniquement pour le dev/test

## 9. Flux camera reseau

Regles specifiques:

- les routes `/api/cameras/*` restent reservees aux sessions admin
- les URLs camera reseau sont validees avant envoi aux workers ou a FFmpeg
- le proxy HLS backend n'accepte que des sources `rtsp://`
- seuls `index.m3u8` et les segments `seg-*.ts` sont servis par le backend
- les repertoires de session HLS sont nettoyes a l'arret

Voir aussi [MODES_CAMERA_RESEAU.md](MODES_CAMERA_RESEAU.md).

---

Voir aussi `AGENTS.md`, `README.md` et `AUDIT.md`.
