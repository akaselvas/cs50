#!/bin/bash
# Set default port if not set
export PORT=${PORT:-10000}

# Run gunicorn
exec gunicorn --worker-class gevent -b 0.0.0.0:$PORT app:app