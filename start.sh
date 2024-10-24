#!/bin/bash

if [[ -z "$RENDER" ]]; then  # Not on Render
  python -c "from app import app; app.run(debug=True)"  # Local development
else # Running on render
  python -c "import gevent.monkey; gevent.monkey.patch_all(ssl=True); from app import app; app.run(debug=False, host='0.0.0.0', port=$PORT)" # Production on Render
fi