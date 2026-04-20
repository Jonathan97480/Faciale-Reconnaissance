#!/bin/bash
# Script d'installation pour Linux

# Création de l'environnement virtuel
python3 -m venv .venv

# Activation de l'environnement virtuel
source .venv/bin/activate

# Installation des dépendances backend (dev incluses)
pip install -r backend/requirements-dev.txt

# Installation des dépendances frontend
cd frontend
npm install
cd ..

echo "Installation terminée."
