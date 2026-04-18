---
mode: "agent"
description: "Create a new configurable runtime parameter end-to-end (DB schema, backend API, React UI, runtime usage, tests) with zero hardcoded operational values."
---

# Nouveau parametre configurable

Objectif: implementer un nouveau parametre runtime de bout en bout dans ce projet (React + Python + base locale) sans valeur metier en dur.

## Entrees

- Nom du parametre: ${input:param_name:Nom technique du parametre}
- Type: ${input:param_type:Type (int|float|bool|string|enum)}
- Valeur par defaut en base: ${input:default_value:Valeur par defaut a persister}
- Contrainte de validation: ${input:validation_rule:Regle de validation (ex: min/max, enum)}
- Ecran React cible: ${input:ui_screen:Ecran ou afficher ce reglage}

## Exigences de livraison

1. Mettre a jour la persistence locale pour stocker et lire ce parametre.
2. Exposer le parametre via API backend (lecture + ecriture).
3. Afficher/editer le parametre dans l interface React.
4. Brancher la consommation runtime backend sur la valeur persistee.
5. Ajouter les tests necessaires:
   - Unitaires: validation et logique metier touchee.
   - Integration API: endpoints configuration.
6. Si la reconnaissance est impactee, couvrir explicitement le cas visage inconnu avec statut inconnu.
7. Respecter la limite de 300 lignes pour chaque fichier Python modifie.

## Contraintes

- Interdire les valeurs operationnelles en dur dans la logique metier.
- Eviter les chemins absolus et identifiants fixes.
- Privilegier des composants React reutilisables et petits.

## Sortie attendue

- Liste des fichiers modifies et resume du role de chacun.
- Description de la migration de donnees si necessaire.
- Liste des tests ajoutes/modifies et comportement verifie.
