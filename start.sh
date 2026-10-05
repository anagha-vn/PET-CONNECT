#!/usr/bin/env bash
# Portable Auto-Launcher for PetConnect
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=========================================================="
echo "   🚀 Launching PetConnect Animal Shelter ML System"
echo "=========================================================="

# Check if virtual environment exists and is valid
if [ ! -d "venv" ] || ! ./venv/bin/python -c "import flask" 2>/dev/null; then
    echo "📦 Creating fresh local virtual environment..."
    rm -rf venv
    python3 -m venv venv
    echo "📥 Installing requirements..."
    ./venv/bin/pip install -r requirements.txt
fi

echo "✅ Environment ready! Launching web server..."
./venv/bin/python app.py
