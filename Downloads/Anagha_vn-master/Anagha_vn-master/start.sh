#!/usr/bin/env bash
# Portable Auto-Launcher for PET CONNECT
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=========================================================="
echo "   🚀 Launching PET CONNECT Animal Shelter & Sanctuary"
echo "=========================================================="

# Check if virtual environment exists and is valid
if [ ! -d "venv" ] || ! ./venv/bin/python -c "import flask" 2>/dev/null; then
    echo "📦 Creating fresh local virtual environment..."
    rm -rf venv
    if ! python3 -m venv venv 2>/dev/null; then
        python3 -m venv --system-site-packages --without-pip venv
    fi
    echo "📥 Installing requirements..."
    ./venv/bin/python -m pip install -r requirements.txt
fi

echo "✅ Environment ready! Launching web server..."
./venv/bin/python app.py
