# Modes Camera Reseau Supportes

Ce document decrit les modes de camera reseau supportes par l'application, leur chemin d'execution, leurs limites, et les points a surveiller en exploitation.

## 1. Vue d'ensemble

L'application sait gerer deux familles de configuration reseau:

- `network_camera_sources`
  - liste de flux reseau saisis directement par URL
  - utile pour ajouter rapidement une source deja connue
- `network_camera_profiles`
  - profils structures par `protocol`, `host`, `port`, `path`, `username`, `password`
  - utile pour les cameras standardisees et le playback web

Limites actuelles:

- maximum `10` sources reseau directes
- maximum `10` profils camera
- retry reseau avec backoff configurable
- monitoring runtime expose par source

## 2. Modes supportes

### RTSP

Usage recommande:

- camera IP classique
- flux principal de detection backend
- cas ou la stabilite et la latence comptent plus que la lecture navigateur directe

Comportement:

- supporte pour la capture backend et la detection
- non lisible directement par le navigateur
- si l'UI doit lire le flux, le backend peut lancer un proxy `RTSP -> HLS`

Notes:

- le proxy HLS n'accepte que des sources `rtsp://`
- le transport RTSP est force en TCP dans FFmpeg
- l'audio RTSP n'est pas expose directement en navigateur sans conversion

### MJPEG

Usage recommande:

- flux HTTP simple
- camera ou outil de test qui expose un `multipart/x-mixed-replace`
- debug ou integration rapide

Comportement:

- supporte comme source reseau backend
- lisible en mode navigateur via URL HTTP
- souvent simple a integrer mais plus lourd en bande passante qu'un flux compresse moderne

### HTTP

Usage recommande:

- endpoint HTTP camera ou passerelle video
- flux lisible par navigateur sans proxy supplementaire

Comportement:

- supporte dans les profils camera
- peut servir au playback direct en UI
- selon le format exact du flux, la lecture backend et la lecture web peuvent avoir des comportements differents

### HLS

Usage recommande:

- playback navigateur avec audio si la camera ou la passerelle expose deja un manifest HLS
- scenario de consultation live depuis l'UI

Comportement:

- supporte dans les profils camera
- si le profil est `hls`, l'UI consomme l'URL directement
- le backend ne convertit pas un flux HLS entrant vers un autre mode

## 3. Choix du mode dans l'application

### `camera_source`

- source principale de capture
- vide = webcam locale
- renseigne = flux principal reseau/fichier pour la boucle de detection

### `network_camera_sources`

- sources secondaires ajoutees dans l'UI
- servent au monitoring multi-flux et a la detection reseau
- accepte des URLs reseau validees (`rtsp`, `http`, `https`)

### `network_camera_profiles`

- abstraction plus propre pour les cameras standards
- l'application construit l'URL finale a partir des champs du profil
- utile pour le playback UI, la decouverte ONVIF, et les integrations repetables

## 4. Playback web: direct vs proxy HLS

Deux chemins existent pour afficher un flux reseau dans l'interface web.

### Playback direct

Utilise quand le profil camera est deja compatible web:

- `hls`
- `http`
- `mjpeg`

Avantages:

- pas de session FFmpeg a gerer
- moins de charge serveur
- moins de latence de mise en place

Limites:

- depend fortement de ce que le navigateur sait lire
- le format reel derriere `http` peut rester heterogene selon la camera

### Proxy HLS backend

Utilise quand le profil est `rtsp`.

Comportement:

- le backend lance FFmpeg
- FFmpeg produit un manifest `index.m3u8` et des segments `seg-*.ts`
- l'UI lit ensuite le flux HLS genere par le backend

Garde-fous actuels:

- seulement pour des sources `rtsp://`
- session ID HLS valide strictement
- seuls `index.m3u8` et `seg-*.ts` sont servis
- nettoyage du repertoire de session a l'arret
- exposition d'un statut runtime HLS via l'API camera

## 5. Validation et securite

L'application refuse deja plusieurs categories d'entrees invalides:

- schema non supporte
- host malforme
- path ambigu ou invalide
- asset HLS inattendu
- source non RTSP envoyee au proxy HLS

Bonnes pratiques:

- preferer un host/IP explicite
- eviter des chemins camera exotiques non testes
- ne pas exposer directement le backend sur Internet sans reverse proxy
- reserver l'acces aux routes `/api/cameras/*` aux sessions admin

## 6. Retry et stabilite reseau

Les flux reseau utilisent un backoff exponentiel borne:

- `network_camera_retry_base_seconds`
- `network_camera_retry_max_seconds`

Effet:

- premiere attente courte en cas d'echec
- delai qui grandit en cas d'echecs consecutifs
- remise a zero apres succes

Le monitoring runtime remonte notamment:

- `last_error`
- `consecutive_failures`
- `retry_delay_seconds`
- `next_retry_at`
- `last_read_duration_ms`

## 7. Quand choisir quoi

Choix recommande par defaut:

- detection backend fiable: `RTSP`
- playback navigateur natif: `HLS`
- debug rapide ou outil local: `MJPEG`
- passerelle HTTP deja en place: `HTTP`

Si une camera fournit uniquement `RTSP` et que tu veux du playback web:

- configurer un profil `rtsp`
- laisser l'application utiliser le proxy HLS backend

Si tu veux minimiser la charge serveur:

- preferer une source deja lisible par navigateur (`HLS` ou `MJPEG`) plutot qu'une conversion RTSP -> HLS

## 8. Limitations actuelles

- pas de lecture RTSP native dans le navigateur
- pas d'interface dediee encore pour afficher le detail des sessions HLS
- pas d'observabilite audio fine par codec/source dans l'UI
- les cas FFmpeg degradés avancés meritent encore un durcissement supplementaire

## 9. Fichiers de reference

- [README.md](README.md)
- [SECURITE.md](SECURITE.md)
- [AUDIT.md](AUDIT.md)
- [backend/app/services/network_camera_pool_service.py](backend/app/services/network_camera_pool_service.py)
- [backend/app/services/hls_gateway_service.py](backend/app/services/hls_gateway_service.py)
