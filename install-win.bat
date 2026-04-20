@echo off
REM Script d'installation pour Windows

REM Création de l'environnement virtuel
python -m venv .venv

REM Activation de l'environnement virtuel
call .venv\Scripts\activate.bat

REM Installation des dépendances backend (dev incluses)
pip install -r backend\requirements-dev.txt

REM Installation des dépendances frontend
cd frontend
call npm install
cd ..

echo Installation terminée.
pause
