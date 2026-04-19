# Reconnaissance Faciale - Python + React

Application de reconnaissance faciale avec:

- Backend Python (`FastAPI` + `SQLite`)
- Frontend React (`Vite`)
- Configuration runtime modifiable depuis l'UI et persistee en base
- Statut `inconnu` si aucun visage n'est reconnu
- Support multi-cameras:
  - webcam locale (camera branchee sur le serveur)
  - flux reseau (RTSP/HTTP/fichier video), jusqu'a 10 sources
  - profils camera standards (RTSP/MJPEG/HTTP/HLS) avec URL generee automatiquement

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
  - ajout/suppression de profils camera standards (protocol/host/port/path/user/pass)
  - endpoint de discovery ONVIF
  - limite de 10 flux reseau
  - budget max de traitement par cycle configurable (2 secondes par defaut)
  - monitoring par flux (erreur, latence lecture, derniere frame, derniere detection)
- Securite/API:
  - endpoint batch production protege par `x-api-key`
  - consultation des logs batch admin protegee par `x-admin-api-key`

## Architecture

- `backend/`
  - `app/services/camera_service.py`: webcam locale + preview live
  - `app/services/network_camera_pool_service.py`: pool de flux reseau
  - `app/services/onvif_discovery_service.py`: decouverte ONVIF (WS-Discovery)
  - `app/services/camera_profile_url_service.py`: generation URLs stream depuis profils
  - `app/services/camera_event_log_service.py`: journal des evenements flux camera
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
- Option GPU NVIDIA (CUDA, recommande pour perf):
```bash
cd backend
pip install --upgrade torch==2.2.2+cu121 torchvision==0.17.2+cu121 torchaudio==2.2.2+cu121 --index-url https://download.pytorch.org/whl/cu121
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
- `network_camera_profiles` (liste, max 10)
- `multi_camera_cycle_budget_seconds` (defaut: `2.0`)
- `enroll_frames_count`
- `face_crop_padding_ratio`
- `inference_device_preference` (`auto|cpu|cuda`)

Notes:

- `camera_source` vide = webcam locale par index (`camera_index`)
- `network_camera_sources` sert aux flux reseau supplementaires
- `network_camera_profiles` permet de declarer des cameras par norme/protocole
- la webcam locale reste utilisable en parallele des flux reseau
- les mots de passe des profils sont masques dans `GET /api/config`
- en mode `auto`, le backend utilise le GPU CUDA si disponible, sinon CPU
- `requirements.txt` installe une pile CPU par defaut; pour CUDA, utiliser la commande GPU ci-dessus

## Endpoints camera supplementaires

- `GET /api/cameras/onvif/discover?timeout_seconds=2`
  - decouverte ONVIF sur le reseau local
- `GET /api/cameras/events?limit=50`
  - logs des erreurs/connexions flux camera
- `GET /api/cameras/profiles/resolved`
  - profils resolus en URLs (version sans credentials)

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

## Outil de test dev (acteurs + flux film)

Script:

- `backend/dev_tools/actor_movie_test_tool.py`

Objectif:

- importer des acteurs depuis une API publique gratuite (TVMaze)
- streamer un film local en flux MJPEG reseau
- brancher ce flux dans la configuration de l'application

Exemples depuis `backend/`:

1. Importer des acteurs d'une serie:
```bash
python dev_tools/actor_movie_test_tool.py import-actors --show "Breaking Bad" --limit 10 --skip-existing
```

2. Diffuser un film local en flux reseau:
```bash
python dev_tools/actor_movie_test_tool.py stream-movie --video "C:\\videos\\film.mp4" --port 8090
```

2bis. Simuler une vraie camera reseau (jitter/pertes/freezes/coupures):
```bash
python dev_tools/actor_movie_test_tool.py stream-movie --video "C:\\videos\\film.mp4" --port 8090 --simulate-real-camera --jitter-ms 150 --drop-frame-probability 0.04 --freeze-probability 0.03 --freeze-seconds 0.8 --outage-probability 0.006 --outage-seconds 2.5
```

3. Configurer l'application pour lire ce flux (mode camera reseau):
```bash
python dev_tools/actor_movie_test_tool.py configure-stream --url "http://127.0.0.1:8090/stream.mjpg" --mode network
```

4. Alternative: utiliser le flux en camera_source principale:
```bash
python dev_tools/actor_movie_test_tool.py configure-stream --url "http://127.0.0.1:8090/stream.mjpg" --mode local
```

### Scenario complet de test live (film + acteurs)

Depuis la racine du projet:

1. Lancer backend + frontend:
```bat
start-dev.bat
```

2. Dans un autre terminal, lancer le flux MJPEG en boucle a partir d'un extrait:
```bash
cd backend
python dev_tools/actor_movie_test_tool.py stream-movie --video "..\\testFlux\\AVENGERS 2.mp4" --host 127.0.0.1 --port 8090 --path /stream.mjpg --fps 10
```

3. Importer les acteurs a partir d'une API publique:
```bash
cd backend
python dev_tools/actor_movie_test_tool.py import-actors --show "Avengers" --limit 10 --skip-existing
```

4. Configurer le flux reseau dans l'application:
```bash
cd backend
python dev_tools/actor_movie_test_tool.py configure-stream --url "http://127.0.0.1:8090/stream.mjpg" --mode network
```

5. Ouvrir Monitoring:

- la grille des flux doit afficher le flux reseau en `actif`
- un clic sur une tuile de flux la passe en flux principal
- les boxes + noms s'affichent sur flux principal et flux reseau

## Notes importantes RTSP/audio

- Backend: RTSP est supporte pour la capture/detection.
- Frontend navigateur: RTSP direct n'est pas lu nativement.
- Pour l'audio en UI web, preferer une source web compatible (HLS/HTTP audio-enabled).
