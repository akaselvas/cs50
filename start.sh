#!/bin/bash

# Monkey-patch
exec python -c "import gevent.monkey; gevent.monkey.patch_all(ssl=True); import app" #  <-- **FIX APP IMPORT PATH HERE**

# Run gunicorn with error logging
exec gunicorn -k gevent app:app -b 0.0.0.0:$PORT --error-logfile -  # <-- **FIX APP:APP IF NEEDED**