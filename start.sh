export PORT=${PORT:-10000}

# Use eventlet if gevent is problematic
gunicorn --worker-class eventlet --workers 2 --timeout 120 app:app -b "0.0.0.0:$PORT" 2>&1

if [[ $? -ne 0 ]]; then
    echo "Gunicorn failed to start. Check logs for details."
    exit 1
fi

echo "Gunicorn started successfully on port $PORT"