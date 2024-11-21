#!/bin/bash
exec python -c "import eventlet; eventlet.monkey_patch()"
source .venv/bin/activate
gunicorn --worker-class eventlet.wsgi.Input --bind 0.0.0.0:$PORT --workers 3 --threads 8 --timeout 0 app:app