#!/bin/bash

export PYTHONPATH=/app
export PORT=5000

pip install --no-cache-dir --upgrade -r /app/requirements.txt

if [ "$ENV" == "local" ] || [ "$ENV" == "dev" ]
then
    echo "Starting DEVELOPMENT Service"
    PYTHONDONTWRITEBYTECODE=1 uvicorn src.main:app --host 0.0.0.0 --port $PORT --reload --no-server-header
else
    echo "Starting PRODUCTION Service"
    uvicorn src.main:app --host 0.0.0.0 --port $PORT --no-server-header
fi