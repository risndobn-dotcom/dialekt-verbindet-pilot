#!/bin/bash

echo "=== S-F-R-G-OS Proof System Installer ==="

# Python-Check
if ! command -v python3 &> /dev/null
then
    echo "Python3 nicht gefunden. Bitte Python3 installieren."
    exit 1
fi

# Virtualenv
if ! python3 -m venv venv &> /dev/null
then
    echo "Konnte venv nicht erstellen. Prüfe Python-Installation."
    exit 1
fi

source venv/bin/activate

# Requirements
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "requirements.txt nicht gefunden, fahre fort ohne zusätzliche Pakete."
fi

# Ordnerstruktur prüfen
mkdir -p proofs

echo "Installation abgeschlossen."
echo "Starte GUI mit: source venv/bin/activate && python gui/gui_app.py"
echo "Starte Dashboard mit: source venv/bin/activate && python dashboard/dashboard.py"
echo "==============================================="
