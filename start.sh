#!/bin/bash

# Explicitly export PORT if not already set (good practice for robustness)
export PORT=${PORT:-10000} # Default to 10000 if PORT is not set (for local testing)

# Use double quotes to ensure proper variable expansion
gunicorn --worker-class gevent --timeout 60 app:app -b "0.0.0.0:$PORT" 2>&1

if [[ $? -ne 0 ]]; then
    echo "Gunicorn failed to start. Check logs for details."
    exit 1
fi

echo "Gunicorn started successfully on port $PORT" # Added for clarity in logs