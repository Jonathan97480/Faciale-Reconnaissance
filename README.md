# Documentation API

Voir [API.md](API.md) pour la documentation complète des endpoints, exemples de requêtes, et codes retour.

Résumé :

- Ajout/suppression/édition de visages
- Analyse d’images (simple ou batch)
- Authentification JWT et clé API
- Logs batch admin

# Reconnaissance Faciale - Python + React

Projet initial avec:

- Backend Python (FastAPI + SQLite)
- Frontend React (Vite)
- Configuration runtime editable depuis UI et persistée en base locale
- Statut `inconnu` si aucun visage reconnu
- Boucle de detection periodique pilotée par la configuration

## Structure

- `backend/`: API locale, persistence, reconnaissance, boucle periodique
- `frontend/`: interface de configuration, gestion de visages, monitoring
- `.github/`: instructions/skills/agents pour les agents IA

## Lancer le backend

1. Ouvrir un terminal dans `backend/`
2. Installer les dependances:

```bash
pip install -r requirements.txt
```

3. Demarrer l'API:

```bash
uvicorn app.main:app --reload
```

API disponible sur `http://127.0.0.1:8000`.

## Lancer le frontend

1. Ouvrir un terminal dans `frontend/`
2. Installer les dependances:

```bash
npm install
```

3. (Optionnel) Configurer l'URL API:

```bash
# .env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

4. Demarrer l'app:

```bash
npm run dev
```

## Tests backend

Depuis `backend/`:

```bash
pytest
```

## Parametres de configuration persistes

- `detection_interval_seconds`
- `match_threshold`
- `camera_index`

Les valeurs par defaut sont inserees en base locale au premier demarrage.
