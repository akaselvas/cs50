#!/bin/bash


# Monkey-patch BEFORE anything imports ssl (including gunicorn and your app)
exec python -c "import gevent.monkey; gevent.monkey.patch_all(ssl=True); import app" # Import app *after* patching, so all subsequent imports are also patched

# Now run gunicorn in the patched environment – it inherits the patched environment due to `exec`
exec gunicorn -k gevent app:app -b 0.0.0.0:$PORT  # or -b :$PORT