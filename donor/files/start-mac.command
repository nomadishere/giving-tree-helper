#!/bin/bash
# Giving Tree helper for Mac: double-click this file (first time: right-click > Open).
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then echo "Python 3 is needed. Install it from python.org, then double-click this again."; read -p "Press Return"; exit 1; fi
python3 -c "import requests" 2>/dev/null || python3 -m pip install --user requests
if [ ! -f .env ]; then cp .env.example .env; echo "Open the file named .env in this folder (TextEdit), paste your token after GT_DONOR_TOKEN= , save, then double-click this again."; open -e .env; read -p "Press Return"; exit 0; fi
python3 donor_worker.py "$@"
echo; read -p "Stopped. Press Return to close."
