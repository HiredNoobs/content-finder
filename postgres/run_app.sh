#!/bin/bash

cd /app
if [ ! -d "venv" ]; then
    python3 -m venv venv
    python3 -m pip install --upgrade pip
fi
source venv/bin/activate  # This almost certainly won't work :)

/app/venv/bin/python3 -m pip install -r requirements.txt
/app/venv/bin/python3 app.py
