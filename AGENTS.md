# AGENTS.md

## Objectif du projet

Construire un logiciel de reconnaissance faciale avec:

- Backend Python pour la capture webcam, la détection/reconnaissance, et l'accès a une base locale
- Frontend React pour piloter toute la configuration, gerer les visages, et afficher les resultats

## Regles non negociables

- Aucune valeur en dur dans le code metier (seuils, intervalles, chemins, camera index, timeouts, etc.)
- Toute valeur operationnelle doit etre configurable depuis l'interface React
- Le backend ne doit pas supposer des chemins absolus ni des identifiants fixes
- Si un visage n'est pas reconnu, le statut doit etre `inconnu`
- Detection periodique par webcam, avec intervalle configurable (valeur de depart recommandee: 3 secondes)

## Contraintes de structure

- Cote React: architecture par composants, petits composants reutilisables
- Cote Python: aucun script/fichier de plus de 300 lignes
- Favoriser une separation claire des responsabilites (capture, inference, persistance, API, UI)
- Eviter les fichiers monolithiques; extraire services/utilitaires quand un fichier grossit

## Architecture cible (a respecter)

- `frontend/`:
  - Composants UI (configuration, gestion des visages, monitoring)
  - Etat central de configuration (store/context) synchronise avec backend
  - Aucun parametre metier en constant locale si editable par l'utilisateur
- `backend/`:
  - Module camera (webcam, cadence de capture)
  - Module reconnaissance (encodage, matching, seuils)
  - Module persistence (base locale + operations CRUD visages)
  - API locale pour exposer lecture/ecriture de configuration et operations de reconnaissance
- `shared/` (optionnel): schemas de configuration et contrats API

## Contrat de configuration

Les agents doivent implementer un flux unique de configuration:

1. Lecture de la configuration depuis la base locale au demarrage
2. Exposition complete via API backend
3. Edition depuis l'interface React
4. Persistance immediate en base locale
5. Prise en compte en temps reel cote backend sans redemarrage si possible

## Base locale

- Utiliser une base locale simple et robuste (SQLite recommande)
- Stocker:
  - Parametres de configuration (intervalle detection, seuils, camera, etc.)
  - Donnees des visages enrolles (metadata + references d'encodage)
  - Historique minimal des detections (optionnel mais recommande)

## Regles de code pour les agents

- Avant de coder, verifier si la fonctionnalite demandee viole une regle ci-dessus
- Refuser d'introduire des constantes metier non configurables
- Ajouter des tests unitaires pour la logique metier critique (matching, statut inconnu, validation config)
- Ajouter des tests d'integration API pour les endpoints de configuration et visages
- Pour toute nouvelle fonctionnalite, documenter rapidement:
  - Parametres exposes a l'UI
  - Valeurs par defaut stockees en base (pas en dur dans la logique)

## Workflow recommande

- Petites PRs par couche (UI, API, reconnaissance, persistance)
- Verification locale minimale avant merge:
  - Lancement backend
  - Lancement frontend
  - Test detection avec webcam
  - Test ajout visage
  - Test reconnaissance visage inconnu

## Definition of Done

Une tache est terminee seulement si:

- Le parametre est editable depuis l'interface React
- La valeur est persistee en base locale
- Le backend utilise la valeur persistee
- Aucun fichier Python modifie ne depasse 300 lignes
- Le comportement `inconnu` est couvre par test si la tache touche la reconnaissance
