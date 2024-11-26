#!/bin/bash

# NO MONKEY PATCHING NEEDED - LET GUNICORN HANDLE GEVENT

# Run gunicorn with error logging and process management
exec gunicorn -k gevent app:app -b 0.0.0.0:$PORT --error-logfile - --workers 3 --threads 2