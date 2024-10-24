#!/bin/bash
exec gunicorn -k gevent --error-logfile - --bind 0.0.0.0:$PORT "app:app" 