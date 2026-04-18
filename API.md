# Documentation de l’API – Reconnaissance Faciale

## Authentification

- Clé API (header `x-api-key`) pour les routes sensibles
- Admin : clé `x-admin-api-key` ou JWT (voir `/api/auth/login`)

## Endpoints principaux

### POST `/api/faces`

Ajoute un visage.

- Body : `{ name, encoding, adresse?, metier?, lieu_naissance?, age?, annee_naissance?, autres_infos_html? }`
- Retour : objet Face

### POST `/api/faces/enroll`

Enrôle un visage via la webcam.

- Body : `{ name, ... }`

### GET `/api/faces`

Liste tous les visages.

### DELETE `/api/faces/{id}`

Supprime un visage.

### POST `/api/recognition/check`

Vérifie une empreinte faciale (embedding).

### POST `/api/recognition/analyze-image`

Analyse une image (binaire ou base64).

### POST `/api/recognition/analyze-images`

Analyse un batch d’images (JSON base64).

### POST `/api/production/recognition/analyze-images`

Batch sécurisé (clé API, logging).

### GET `/api/admin/batch-logs/`

Consulte les logs batch (clé admin ou JWT).

### POST `/api/auth/login`

Authentification JWT admin.

- Body (form) : `username`, `password`
- Retour : `{ access_token }`

## Exemples de requêtes

```http
POST /api/faces
Content-Type: application/json
{
  "name": "Alice",
  "adresse": "Paris",
  "age": 30
}
```

```http
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded
username=admin&password=adminpass
```

## Codes retour

- 200 : OK
- 201 : Créé
- 401 : Non autorisé
- 403 : Interdit
- 404 : Introuvable
- 422 : Données invalides

## Voir aussi

- SECURITE.md
- AGENTS.md
