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

2. `[fait]` Supprimer les credentials par defaut dangereux
Fichiers:
- `backend/app/api/routes/auth.py`
- `backend/app/services/secret_crypto_service.py`

Realise:
- Suppression des valeurs par defaut `admin`, `adminpass`, `change_me_jwt`
- Suppression de la valeur par defaut `dev-insecure-change-me`
- Le backend repond desormais `503` sur les endpoints d'auth si `ADMIN_USERNAME`, `ADMIN_PASSWORD` ou `JWT_SECRET` ne sont pas configures

Note:
- Le chiffrement de configuration requiert maintenant `FACE_CONFIG_SECRET`

3. `[fait]` Remplacer la crypto maison
Fichiers:
- `backend/app/services/secret_crypto_service.py`
- `backend/requirements.txt`

Realise:
- Migration d'ecriture vers `enc:v2:`
- Chiffrement via `cryptography.fernet`
- Compatibilite de lecture maintenue pour l'ancien format `enc:v1:`
- Tests unitaires ajoutes sur le service de chiffrement

4. `[fait]` Separer biometrie et identite en 2 tables
Fichiers:
- `backend/app/core/database.py`
- `backend/app/services/face_service.py`

Realise:
- Introduction de `face_profiles` et `face_embeddings`
- Migration des donnees legacy depuis `faces`
- Reconnaissance et listing branches sur les nouvelles tables

5. `[fait]` Supprimer ou securiser `autres_infos_html`
Fichiers:
- `frontend/src/components/FaceManager.jsx`
- `backend/app/core/schemas.py`
- `backend/app/services/face_service.py`

Realise:
- Suppression du rendu HTML brut via `dangerouslySetInnerHTML`
- Affichage en texte brut cote frontend
- Renommage du champ API en `autres_infos`
- Compatibilite de lecture de l'ancien input `autres_infos_html`

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
- `pytest` backend: `66 passed`

### Priorite 2 - Important

9. `[fait]` Optimiser la reconnaissance avec cache memoire
Fichier:
- `backend/app/services/recognition_service.py`

Realise:
- Chargement des embeddings en memoire avec cache lie au chemin de base locale
- Rechargement automatique si la base cible change
- Invalidation explicite sur creation et suppression de visage

10. `[fait]` Eviter la reconfiguration GPU a chaque boucle
Fichier:
- `backend/app/services/detection_loop.py`

Realise:
- La boucle applique le device uniquement quand la preference change
- Le cache local de preference est reinitialise en cas d'erreur runtime

11. `[fait]` Ajouter des metriques de performance
Fichier:
- `backend/app/services/detection_loop.py`

Realise:
- Mesure des temps capture, inference, DB et duree de cycle
- Exposition des metriques dans `detection_loop.status()`

12. `[fait]` Decoupler config et runtime
Fichier:
- `backend/app/services/config_service.py`

Realise:
- `read_config()` ne configure plus l'inference
- `inference_device_active` reflete l'etat runtime courant sans effet de bord
- `update_config()` applique explicitement la nouvelle preference pour prise en compte immediate

13. `[fait]` Refactor `MonitoringPanel`
Fichier:
- `frontend/src/components/MonitoringPanel.jsx`

Realise:
- Extraction du flux principal, de la grille des flux, de l'historique reutilisable et du panneau d'analyse image
- Reduction de la taille et de la complexite du composant orchestrateur

14. `[fait]` Refactor `ConfigPanel`
Fichier:
- `frontend/src/components/ConfigPanel.jsx`

Realise:
- Extraction des helpers de payload
- Separation des blocs UI general, flux reseau et profils camera
- Reduction de la taille et de la complexite du composant principal

15. `[fait]` Unifier le client API frontend
Fichier:
- `frontend/src/api/client.js`

Realise:
- `deleteFace` passe par le meme pipeline d'erreur que le reste
- Ajout de `credentials: include`
- Centralisation du parsing d'erreur

16. `[fait]` Ajouter rate limiting API production
Fichier:
- `backend/app/api/routes/production_recognition.py`

Realise:
- Limiteur en memoire par client/API key sur l'endpoint production
- Parametres exposes dans la configuration backend/frontend
- Reponse `429` avec header `Retry-After`

17. `[fait]` Separer `requirements.txt` et `requirements-dev.txt`
Fichier:
- `backend/requirements.txt`
- `backend/requirements-dev.txt`

Realise:
- `requirements.txt` conserve les dependances runtime
- `requirements-dev.txt` ajoute les dependances de test/developpement
- Scripts d'installation et README aligns sur cette separation

### Priorite 3 - Confort / Scaling

18. `[fait]` Ajouter cache config
Fichier:
- `backend/app/services/config_service.py`

Realise:
- Cache memoire de la configuration
- Invalidation explicite sur `update_config()`
- Refresh automatique si la base SQLite change directement

19. `[fait]` Remplacer polling frontend par WebSocket
Fichier:
- `frontend/src/components/MonitoringPanel.jsx`

Realise:
- Ajout d'un flux WebSocket backend pour le snapshot de monitoring
- Connexion frontend live avec reconnexion automatique
- Suppression du polling periodique principal cote UI
- Proxy Vite aligne pour supporter les upgrades WebSocket en dev

20. `[fait]` Ajouter ESLint et format frontend
Fichiers:
- `frontend/package.json`
- `frontend/eslint.config.js`
- `frontend/.prettierrc.json`
- `frontend/.prettierignore`

Realise:
- Ajout des scripts `lint`, `format` et `format:check`
- Installation et configuration ESLint pour React/Vite
- Installation et configuration Prettier
- Frontend reformate et verifie localement

21. `[fait]` Ameliorer calibration seuil reconnaissance
Fichiers:
- `backend/app/services/recognition_service.py`
- `backend/app/core/schemas.py`
- `backend/app/services/config_service.py`
- `frontend/src/components/ConfigGeneralSettings.jsx`

Realise:
- Ajout du parametre `match_margin_threshold`
- Le backend retourne `inconnu` si deux candidats sont trop proches
- Parametre expose dans l'API, persiste en base et editable depuis l'UI
- Tests ajoutes sur l'ambiguite entre meilleur et second match

22. `[fait]` Ajouter backoff camera reseau
Fichiers:
- `backend/app/services/network_camera_pool_service.py`
- `backend/app/services/config_service.py`
- `frontend/src/components/ConfigGeneralSettings.jsx`

Realise:
- Backoff exponentiel borne sur les reconnexions de flux reseau
- Parametres `network_camera_retry_base_seconds` et `network_camera_retry_max_seconds`
- Parametres exposes dans l'API, persistes en base et editables depuis l'UI
- Exposition runtime du prochain retry et du delai courant

23. `[fait]` Uniformiser monitoring camera locale vs reseau
Fichiers:
- `backend/app/services/camera_service.py`
- `backend/app/api/routes/recognition.py`
- `frontend/src/components/MonitoringPanel.jsx`

Realise:
- Exposition d'un statut runtime local aligne sur les flux reseau
- Ajout des infos `has_frame`, erreurs, timestamps et temps de lecture pour la camera locale
- Monitoring frontend unifie entre source locale et sources reseau
- HUD principal aligne sur l'etat runtime du flux selectionne

24. `[fait]` Ajouter tests avances reconnaissance
Dossier:
- `backend/tests/`

Realise:
- Ajout de cas limites sur la reconnaissance unitaire
- Validation du choix du meilleur match
- Validation de l'ignorance des embeddings invalides ou vides
- Validation de l'agregation et de la priorisation des detections sauvegardees

25. `[fait]` Ameliorer README securite + prod
Fichiers:
- `README.md`
- `SECURITE.md`

Realise:
- Documentation des variables d'environnement obligatoires et optionnelles
- Clarification de l'auth admin JWT par cookie HTTP-only
- Documentation de l'API production `x-api-key`
- Ajout des recommandations de deploiement, CORS et rate limiting

26. `[fait]` Retirer l'usage legacy restant de la table `faces`
Fichiers:
- `backend/app/core/database.py`
- `backend/tests/unit/test_database_migration.py`

Realise:
- Migration automatique des anciennes bases contenant `faces`
- Migration du schema legacy `detections` qui referencait encore `faces`
- Suppression de la table `faces` apres transfert
- Les nouvelles bases ne recreent plus la table legacy

## Lot Realise

Ce qui est effectivement termine a ce stade:
- Authentification JWT avec expiration
- Protection des routes sensibles
- Session frontend avec login/logout
- Remplacement de la crypto maison par `Fernet` avec compatibilite legacy
- Decouplage lecture config / runtime inference
- Arret de la reconfiguration inference a chaque cycle de detection
- Cache memoire des embeddings avec invalidation
- Metriques runtime de capture, inference et DB
- Refactor du `MonitoringPanel` en sous-composants
- Refactor du `ConfigPanel` en sections et helpers
- Rate limiting configurable sur l'API production
- Separation des dependances runtime et dev
- Separation biometrie / identite en tables distinctes
- Cache memoire de la configuration avec refresh sur changement DB
- Documentation README/SECURITE alignee sur l'etat reel du projet
- Non exposition des embeddings via API
- Suppression du rendu HTML brut pour les infos visage
- Harmonisation du client API frontend
- Tests avances de reconnaissance et de persistance detection
- Suppression finale de la dependance legacy a la table `faces`
- Monitoring frontend branche sur un flux WebSocket live
- Outillage ESLint/Prettier actif sur le frontend
- Calibration du matching avec marge configurable entre meilleurs scores
- Monitoring local/reseau uniformise autour d'un contrat runtime commun
- Backoff configurable sur les tentatives de reconnexion des flux reseau
- Validation et durcissement des URLs/sources de flux cameras
- Observabilite HLS enrichie pour diagnostic des sessions de playback proxy
- Batterie de tests backend mise a jour et verifiee

27. `[fait]` Introduire une couche de tests frontend
Fichiers:
- `frontend/package.json`
- `frontend/vite.config.js`
- `frontend/src/components/LoginPanel.test.jsx`
- `frontend/src/components/configPanelUtils.test.js`

Realise:
- Ajout de `Vitest` et `Testing Library`
- Environnement `jsdom` configure pour les tests UI
- Tests sur le flux login/bootstrap admin
- Tests sur la normalisation du payload de configuration

28. `[fait]` Continuer le durcissement reseau des flux cameras
Fichiers:
- `backend/app/core/schemas.py`
- `backend/app/services/network_url_validation_service.py`
- `backend/app/services/camera_profile_url_service.py`
- `backend/app/services/hls_gateway_service.py`

Realise:
- Validation stricte des schemas d'URL reseau supportes
- Validation du `host` et du `path` des profils camera
- Rejet des sources libres invalides des l'etape de validation config
- Garde-fous supplementaires sur les URLs envoyees au worker reseau et a FFmpeg

29. `[fait]` Affiner l'observabilite des flux audio/video HLS
Fichiers:
- `backend/app/services/hls_gateway_service.py`
- `backend/tests/unit/test_hls_gateway_service.py`
- `backend/tests/integration/test_cameras_api.py`

Realise:
- Enrichissement du statut des sessions HLS avec `manifest_ready`, `manifest_updated_at` et `segment_count`
- Exposition du dernier code de sortie FFmpeg et d'une erreur resumee exploitable via l'API
- Ajout d'un `uptime_seconds` pour diagnostiquer une session qui demarre puis tombe vite
- Couverture unitaire du calcul de statut et verification d'integration sur l'endpoint sessions

30. `[fait]` Etendre les tests frontend aux composants de monitoring/config
Fichiers:
- `frontend/src/components/ConfigPanel.test.jsx`
- `frontend/src/components/MonitoringFeedGrid.test.jsx`
- `frontend/src/components/MonitoringMainFeed.test.jsx`

Realise:
- Validation du flux d'ajout de source reseau et de la validation profil camera dans `ConfigPanel`
- Validation de la selection et de la suppression d'un flux secondaire dans `MonitoringFeedGrid`
- Validation des transitions d'etat visuel du flux principal dans `MonitoringMainFeed`
- Couverture frontend portee a 12 tests via `Vitest` et `Testing Library`

31. `[fait]` Continuer le durcissement des flux cameras sur les chemins HLS et FFmpeg
Fichiers:
- `backend/app/services/hls_gateway_service.py`
- `backend/app/api/routes/cameras.py`
- `backend/tests/unit/test_hls_gateway_service.py`
- `backend/tests/integration/test_cameras_api.py`

Realise:
- Le proxy HLS refuse desormais toute source non `rtsp://`
- Le service des assets HLS n'accepte plus que `index.m3u8` et les segments `seg-*.ts`
- Validation stricte du format d'identifiant de session HLS
- Nettoyage du repertoire de session lors de l'arret pour eviter les segments orphelins exposes
- Ajout de `-nostdin` au lancement FFmpeg pour reduire les interactions non necessaires

32. `[fait]` Ajouter une doc dediee aux modes camera reseau supportes
Fichiers:
- `MODES_CAMERA_RESEAU.md`
- `README.md`
- `SECURITE.md`

Realise:
- Documentation centralisee des modes `RTSP`, `MJPEG`, `HTTP`, `HLS`
- Clarification du choix entre playback direct navigateur et proxy HLS backend
- Rappel des garde-fous de validation, retry reseau et limitations actuelles
- Alignement de la doc generale et securite avec cette nouvelle reference

33. `[fait]` Optimiser la boucle de detection pour reduire les cycles sans resultat utile
Fichiers:
- `backend/app/services/detection_loop.py`
- `backend/app/services/recognition_service.py`
- `backend/tests/unit/test_recognition_unknown.py`

Realise:
- Mutualisation de la lecture config pour reconnaitre plusieurs visages d'une meme frame
- Reconnaissance par lot pour eviter une relecture config par visage
- Suppression des ecritures SQLite vides quand aucune face n'a ete detectee sur un cycle
- Conservation du statut `inconnu` quand une detection negative explicite est reellement produite

34. `[fait]` Reduire le cout de lecture multi-flux reseau quand certaines sources sont inactives
Fichiers:
- `backend/app/services/network_camera_pool_service.py`
- `backend/app/services/detection_loop.py`
- `backend/tests/unit/test_network_camera_backoff.py`
- `backend/tests/integration/test_recognition_preview_api.py`

Realise:
- Filtrage des frames reseau trop anciennes avant traitement dans la boucle de detection
- Exposition de `latest_frame_age_seconds` sur les flux reseau pour diagnostiquer les sources stale
- Ajout de `skipped_stale_sources` dans les metriques runtime de loop
- Separation des temps `decode_ms`, `extract_ms`, `matching_ms` et conservation de `db_ms`

35. `[fait]` Revoir la charge du playback HLS si plusieurs sessions sont ouvertes en parallele
Fichiers:
- `backend/app/services/hls_gateway_service.py`
- `backend/app/api/routes/cameras.py`
- `backend/app/services/config_service.py`
- `backend/app/core/database.py`

Realise:
- Ajout de `hls_proxy_max_sessions` pour limiter les sessions FFmpeg paralleles
- Ajout de `hls_proxy_idle_ttl_seconds` pour expirer les sessions HLS inactives
- Eviction LRU des sessions HLS les moins recentes quand la limite est atteinte
- Application du TTL sur listing, reutilisation et service des assets HLS

36. `[fait]` Evaluer un echantillonnage adaptatif des flux les plus instables
Fichiers:
- `backend/app/services/detection_loop.py`
- `backend/app/services/config_service.py`
- `backend/app/core/database.py`
- `frontend/src/components/ConfigGeneralSettings.jsx`

Realise:
- Ajout de `unstable_source_failure_threshold` et `unstable_source_cycle_skip`
- Sous-echantillonnage des flux reseau avec echecs consecutifs eleves
- Ajout de `skipped_unstable_sources` dans les metriques runtime
- Parametres exposes dans l'UI, persistes en base et pris en compte a chaud

37. `[fait]` Ajouter une vue UI des metriques runtime detaillees pour verifier les gains en exploitation
Fichiers:
- `frontend/src/components/MonitoringRuntimeMetricsPanel.jsx`
- `frontend/src/components/MonitoringPanel.jsx`
- `frontend/src/app.css`

Realise:
- Ajout d'un panneau UI lisible pour les temps `capture`, `decode`, `extract`, `matching`, `db` et `cycle`
- Ajout des compteurs `processed_sources`, `results_count`, `skipped_stale_sources`, `skipped_unstable_sources`
- Mise en avant des sources reseau degradees avec age de frame, retry, echecs consecutifs et erreur courante
- Remplacement du dump JSON brut du loop runtime par une vue exploitable en monitoring live

## Prochain Lot Recommande

Ordre conseille pour la suite:
1. Continuer le durcissement FFmpeg sur les erreurs transitoires et la gestion des timeouts
2. Ajouter des alertes de saturation HLS quand la limite de sessions est atteinte
3. Etendre les tests UI au parcours playback camera et metriques detaillees
4. Evaluer un affichage compact de l'historique perf sur plusieurs cycles
