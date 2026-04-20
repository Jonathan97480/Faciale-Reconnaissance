## Suivi Audit

Derniere mise a jour: 2026-04-20

Statuts:
- `[fait]` implemente et verifie
- `[en cours]` commence mais non termine
- `[a faire]` non implemente

### Priorite 1 - Critique

1. `[fait]` Securiser les routes sensibles
Fichiers:
- `backend/app/api/routes/auth.py`
- `backend/app/api/routes/faces.py`
- `backend/app/api/routes/config.py`
- `backend/app/api/routes/recognition.py`
- `backend/app/api/routes/enrollment.py`
- `backend/app/api/routes/cameras.py`
- `backend/app/api/routes/admin_batch_logs.py`

Realise:
- Ajout d'une authentification obligatoire sur les routes backend sensibles via `Depends(get_current_user)`
- Ajout des endpoints `login`, `logout` et `me`
- Session frontend basee sur cookie HTTP-only

2. `[fait]` Supprimer les credentials JWT par defaut dangereux dans l'auth
Fichiers:
- `backend/app/api/routes/auth.py`

Realise:
- Suppression des valeurs par defaut `admin`, `adminpass`, `change_me_jwt`
- Le backend repond desormais `503` sur les endpoints d'auth si `ADMIN_USERNAME`, `ADMIN_PASSWORD` ou `JWT_SECRET` ne sont pas configures

Reste a faire:
- `backend/app/services/secret_crypto_service.py` utilise encore `dev-insecure-change-me`

3. `[a faire]` Remplacer la crypto maison
Fichiers:
- `backend/app/services/secret_crypto_service.py`

Objectif:
- Remplacer XOR + SHA256 par une solution standard type `cryptography.fernet`

4. `[a faire]` Separer biometrie et identite en 2 tables
Fichiers:
- `backend/app/core/database.py`
- `backend/app/services/face_service.py`

Objectif:
- Introduire une separation `face_profiles` / `face_embeddings`

5. `[fait]` Supprimer ou securiser `autres_infos_html`
Fichiers:
- `frontend/src/components/FaceManager.jsx`

Realise:
- Suppression du rendu HTML brut via `dangerouslySetInnerHTML`
- Affichage en texte brut cote frontend

Reste a faire:
- Renommer le champ API et la persistence pour enlever l'ambiguite HTML

6. `[fait]` Ne pas exposer les embeddings via API
Fichiers:
- `backend/app/core/schemas.py`
- `backend/app/services/face_service.py`
- `frontend/src/components/FaceManager.jsx`

Realise:
- `FaceRecord` renvoie `has_encoding` au lieu de `encoding`
- Le frontend ne depend plus de la valeur de l'embedding

7. `[fait]` Ajouter expiration JWT et vraie auth
Fichiers:
- `backend/app/api/routes/auth.py`
- `frontend/src/context/AuthContext.jsx`
- `frontend/src/components/LoginPanel.jsx`
- `frontend/src/api/client.js`

Realise:
- JWT avec `iat` et `exp`
- Validation robuste du token
- Login frontend avec maintien de session

8. `[fait]` Ajouter tests securite et auth
Fichiers:
- `backend/tests/auth_utils.py`
- `backend/tests/integration/test_auth_api.py`
- `backend/tests/integration/test_admin_batch_logs_api.py`
- `backend/tests/integration/test_config_api.py`
- `backend/tests/integration/test_faces_api.py`
- `backend/tests/integration/test_enrollment_api.py`
- `backend/tests/integration/test_recognition_image_api.py`
- `backend/tests/integration/test_recognition_latest_api.py`
- `backend/tests/integration/test_recognition_preview_api.py`
- `backend/tests/integration/test_cameras_api.py`

Verification:
- `pytest` backend: `41 passed`

### Priorite 2 - Important

9. `[a faire]` Optimiser la reconnaissance avec cache memoire
Fichier:
- `backend/app/services/recognition_service.py`

10. `[a faire]` Eviter la reconfiguration GPU a chaque boucle
Fichier:
- `backend/app/services/detection_loop.py`

11. `[a faire]` Ajouter des metriques de performance
Fichier:
- `backend/app/services/detection_loop.py`

12. `[a faire]` Decoupler config et runtime
Fichier:
- `backend/app/services/config_service.py`

13. `[a faire]` Refactor `MonitoringPanel`
Fichier:
- `frontend/src/components/MonitoringPanel.jsx`

14. `[a faire]` Refactor `ConfigPanel`
Fichier:
- `frontend/src/components/ConfigPanel.jsx`

15. `[fait]` Unifier le client API frontend
Fichier:
- `frontend/src/api/client.js`

Realise:
- `deleteFace` passe par le meme pipeline d'erreur que le reste
- Ajout de `credentials: include`
- Centralisation du parsing d'erreur

16. `[a faire]` Ajouter rate limiting API production
Fichier:
- `backend/app/api/routes/production_recognition.py`

17. `[a faire]` Separer `requirements.txt` et `requirements-dev.txt`
Fichier:
- `backend/requirements.txt`

### Priorite 3 - Confort / Scaling

18. `[a faire]` Ajouter cache config
Fichier:
- `backend/app/services/config_service.py`

19. `[a faire]` Remplacer polling frontend par WebSocket
Fichier:
- `frontend/src/components/MonitoringPanel.jsx`

20. `[a faire]` Ajouter ESLint et format frontend
Fichier:
- `frontend/package.json`

21. `[a faire]` Ameliorer calibration seuil reconnaissance
Fichier:
- `backend/app/services/recognition_service.py`

22. `[a faire]` Ajouter backoff camera reseau
Fichier:
- `backend/app/services/network_camera_pool_service.py`

23. `[a faire]` Uniformiser monitoring camera locale vs reseau
Fichier:
- `backend/app/services/camera_service.py`

24. `[a faire]` Ajouter tests avances reconnaissance
Dossier:
- `backend/tests/`

25. `[a faire]` Ameliorer README securite + prod
Fichier:
- `README.md`

## Lot Realise

Ce qui est effectivement termine a ce stade:
- Authentification JWT avec expiration
- Protection des routes sensibles
- Session frontend avec login/logout
- Non exposition des embeddings via API
- Suppression du rendu HTML brut pour les infos visage
- Harmonisation du client API frontend
- Batterie de tests backend mise a jour et verifiee

## Prochain Lot Recommande

Ordre conseille pour la suite:
1. Remplacer `secret_crypto_service.py`
2. Decoupler `read_config()` de la logique runtime IA
3. Eviter `configure_inference_device()` a chaque cycle
4. Ajouter un cache memoire des embeddings
