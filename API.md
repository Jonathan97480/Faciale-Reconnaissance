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
  "network_camera_profiles": [],
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
- `network_camera_profiles` (`NetworkCameraProfile[]`, max 10)
- `multi_camera_cycle_budget_seconds` (`float`, `0.1..10`)
- `enroll_frames_count` (`int`, `1..30`)
- `face_crop_padding_ratio` (`float`, `0..1`)

`NetworkCameraProfile`:

- `name` (`string`)
- `protocol` (`rtsp|mjpeg|http|hls`)
- `host` (`string`)
- `port` (`int`)
- `path` (`string`)
- `username` (`string`)
- `password` (`string`) (masque en lecture)
- `has_password` (`bool`) (info uniquement)
- `onvif_url` (`string`, optionnel)
- `enabled` (`bool`)

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
  "network_camera_profiles": [
    {
      "name": "Entrance Cam",
      "protocol": "rtsp",
      "host": "192.168.1.20",
      "port": 554,
      "path": "/stream1",
      "username": "admin",
      "password": "admin",
      "onvif_url": "",
      "enabled": true
    }
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

## 5) Camera Operations

### GET `/api/cameras/onvif/discover?timeout_seconds=2`

Discovery ONVIF (WS-Discovery multicast).

Reponse:

```json
{
  "count": 1,
  "devices": [
    {
      "ip": "192.168.1.20",
      "port": 3702,
      "xaddrs": ["http://192.168.1.20/onvif/device_service"],
      "scopes": "onvif://..."
    }
  ]
}
```

### GET `/api/cameras/events?limit=50`

Journal des evenements flux camera (start/connect/error/stop).

### GET `/api/cameras/profiles/resolved`

Retourne les profils avec URL stream resolue (sans credentials) et URL de lecture web si disponible.

### GET `/api/cameras/alerts`

Alertes operationnelles derivees du runtime:

- `camera_down`
- `high_read_latency`
- `detection_stale`

### POST `/api/cameras/playback/start?profile_name=...`

Demarre/retourne une URL de lecture web:

- mode `direct` pour profils `hls/http/mjpeg`
- mode `hls_proxy` pour `rtsp` (FFmpeg requis)

Exemple reponse proxy:

```json
{
  "mode": "hls_proxy",
  "profile_name": "Entrance Cam",
  "session_id": "abc123",
  "playback_url": "/api/cameras/hls/abc123/index.m3u8",
  "audio_expected": true
}
```

### GET `/api/cameras/playback/sessions`

Liste des sessions HLS actives.

### DELETE `/api/cameras/playback/sessions/{session_id}`

Arrete une session HLS.

### GET `/api/cameras/hls/{session_id}/{filename}`

Recupere les assets HLS (`.m3u8`, `.ts`) de la session.

## 6) Admin logs

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

## 7) Auth admin

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
