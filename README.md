# Reconnaissance Faciale - Python + React

Application de reconnaissance faciale avec:

- Backend Python (`FastAPI` + `SQLite`)
- Frontend React (`Vite`)
- Configuration runtime modifiable depuis l'UI et persistee en base
- Statut `inconnu` si aucun visage n'est reconnu
- Support multi-cameras:
  - webcam locale (camera branchee sur le serveur)
  - flux reseau (RTSP/HTTP/fichier video), jusqu'a 10 sources

## Fonctionnalites principales

- Gestion des visages:
  - ajout manuel (`/api/faces`)
  - enrollment depuis la webcam (`/api/faces/enroll`)
  - suppression (`/api/faces/{id}`)
- Reconnaissance:
  - boucle periodique configurable
  - analyse image unitaire et batch
  - preview live MJPEG pour la camera locale
- Multi-camera reseau:
  - ajout/suppression dynamique des sources dans l'UI
  - limite de 10 flux reseau
  - budget max de traitement par cycle configurable (2 secondes par defaut)
- Securite/API:
  - endpoint batch production protege par `x-api-key`
  - consultation des logs batch admin protegee par `x-admin-api-key`

## Architecture

- `backend/`
  - `app/services/camera_service.py`: webcam locale + preview live
  - `app/services/network_camera_pool_service.py`: pool de flux reseau
  - `app/services/detection_loop.py`: orchestration detection multi-sources
  - `app/services/config_service.py`: lecture/ecriture config en base
  - `app/core/database.py`: schema SQLite + defaults
- `frontend/`
  - `src/components/ConfigPanel.jsx`: configuration runtime (locale + reseau)
  - `src/components/MonitoringPanel.jsx`: monitoring et preview
  - `src/api/client.js`: client API frontend

## Installation

### Installation automatique

- Windows:
```bat
install-win.bat
```
- Linux:
```bash
bash install-linux.sh
```

### Installation manuelle

- Backend:
```bash
cd backend
pip install -r requirements.txt
```
- Frontend:
```bash
cd frontend
npm install
```

## Lancement

### Option recommandee (Windows)

Depuis la racine:

```bat
start-dev.bat
```

Le script:

- demarre le backend sur `127.0.0.1:8001`
- attend que l'API soit disponible
- demarre ensuite le frontend

### Lancement manuel

- Backend:
```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8001
```
- Frontend:
```bash
cd frontend
npm run dev
```

Le frontend utilise un proxy Vite (`/api`) vers `http://127.0.0.1:8001`.

## Configuration runtime (persistee SQLite)

Champs principaux:

- `detection_interval_seconds`
- `match_threshold`
- `camera_index`
- `camera_source`
- `network_camera_sources` (liste, max 10)
- `multi_camera_cycle_budget_seconds` (defaut: `2.0`)
- `enroll_frames_count`
- `face_crop_padding_ratio`

Notes:

- `camera_source` vide = webcam locale par index (`camera_index`)
- `network_camera_sources` sert aux flux reseau supplementaires
- la webcam locale reste utilisable en parallele des flux reseau

## Tests

- Backend:
```bash
cd backend
pytest
```
- Frontend build:
```bash
cd frontend
npm run build
```

## Documentation API

Voir [API.md](API.md) pour:

- la liste complete des endpoints
- les payloads
- des exemples de requetes
- les codes de retour
