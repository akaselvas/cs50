#!/bin/bash

# Monkey-patch before importing other modules that use sockets
gevent monkey -v -p

# Now run Gunicorn
exec gunicorn -k gevent --worker-class socketio.sgunicorn.GeventSocketIOWorker --bind 0.0.0.0:$PORT "app:app"