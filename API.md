# Documentation API - Reconnaissance Faciale

Base URL en local:

- `http://127.0.0.1:8001/api`

## Authentification

- `x-api-key`: requis pour les endpoints production.
- `x-admin-api-key`: requis pour les endpoints admin batch logs.
- JWT admin via `/api/auth/login` disponible.

## 1) Configuration

### GET `/api/config`

Retourne la configuration runtime courante.

Exemple de reponse:

```json
{
  "detection_interval_seconds": 3.0,
  "match_threshold": 0.6,
  "camera_index": 0,
  "camera_source": "",
  "network_camera_sources": [],
  "multi_camera_cycle_budget_seconds": 2.0,
  "enroll_frames_count": 5,
  "face_crop_padding_ratio": 0.2
}
```

### PUT `/api/config`

Met a jour la configuration runtime (persistance immediate en SQLite).

Champs:

- `detection_interval_seconds` (`float > 0`)
- `match_threshold` (`float 0..1`)
- `camera_index` (`int >= 0`)
- `camera_source` (`string`, vide = webcam locale)
- `network_camera_sources` (`string[]`, max 10)
- `multi_camera_cycle_budget_seconds` (`float`, `0.1..10`)
- `enroll_frames_count` (`int`, `1..30`)
- `face_crop_padding_ratio` (`float`, `0..1`)

Exemple:

```json
{
  "detection_interval_seconds": 3.0,
  "match_threshold": 0.6,
  "camera_index": 1,
  "camera_source": "",
  "network_camera_sources": [
    "rtsp://cam1/stream",
    "rtsp://cam2/stream"
  ],
  "multi_camera_cycle_budget_seconds": 2.0,
  "enroll_frames_count": 5,
  "face_crop_padding_ratio": 0.2
}
```

## 2) Visages

### GET `/api/faces`

Liste des visages enroles.

### POST `/api/faces`

Ajoute un visage.

Body:

- `name` (obligatoire)
- `encoding` (optionnel)
- `adresse`, `metier`, `lieu_naissance`, `age`, `annee_naissance`, `autres_infos_html` (optionnels)

### DELETE `/api/faces/{face_id}`

Supprime un visage.

### POST `/api/faces/enroll`

Enrole un visage via la webcam locale.

Body:

```json
{
  "name": "Alice"
}
```

## 3) Reconnaissance

### POST `/api/recognition/check`

Verification directe d'un embedding.

### GET `/api/recognition/loop/status`

Etat de la boucle de detection.

Exemple de reponse:

```json
{
  "loop": { "running": true },
  "capture_settings": {
    "detection_interval_seconds": 3.0,
    "camera_index": 1
  },
  "network_cameras": {
    "configured_sources_count": 2,
    "configured_sources": [
      "rtsp://cam1/stream",
      "rtsp://cam2/stream"
    ]
  }
}
```

### GET `/api/recognition/latest`

Derniere detection calculee.

### GET `/api/recognition/history?limit=10`

Historique des detections (`limit` entre `1` et `50`).

### GET `/api/recognition/preview`

Snapshot JPEG de la camera locale de preview.

### GET `/api/recognition/preview/stream`

Flux MJPEG continu (preview locale).

### POST `/api/recognition/analyze-image`

Analyse d'une image brute (body binaire).

Headers:

- `Content-Type: image/*` ou `application/octet-stream`

### POST `/api/recognition/analyze-images`

Analyse batch d'images base64.

Exemple:

```json
{
  "items": [
    {
      "filename": "face1.jpg",
      "content_type": "image/jpeg",
      "image_base64": "..."
    }
  ]
}
```

## 4) Production (securise)

### POST `/api/production/recognition/analyze-images`

Meme principe que `analyze-images`, mais protege par API key.

Header requis:

- `x-api-key: <FACE_API_KEY>`

## 5) Admin logs

### GET `/api/admin/batch-logs/`

Recupere les logs batch.

Query params:

- `limit` (1..100)
- `offset` (>=0)
- `endpoint` (optionnel)
- `date_from` (optionnel)
- `date_to` (optionnel)

Header requis:

- `x-admin-api-key: <FACE_ADMIN_API_KEY>`

## 6) Auth admin

### POST `/api/auth/login`

Authentification admin (form-urlencoded).

Body:

- `username`
- `password`

Reponse:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

## Codes de retour usuels

- `200`: succes
- `201`: cree
- `204`: supprime
- `400`: payload invalide metier
- `401`: non autorise
- `404`: ressource introuvable
- `415`: content-type non supporte
- `422`: validation schema
- `503`: service indisponible (ex: camera ou cle API manquante)

## Voir aussi

- `README.md`
- `SECURITE.md`
- `AGENTS.md`
