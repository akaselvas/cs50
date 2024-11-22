# export PORT=${PORT:-10000}
#!/bin/bash

# Monkey patch *before* anything else!
# This needs to happen *within* the activated virtual environment.
exec python -c "import eventlet; eventlet.monkey_patch()" # Use exec python -c


# Activate the virtual environment
source .venv/bin/activate # Add this line to activate the venv


# Install dependencies (can be done before patching if preferred)
pip install -r requirements.txt

# Set the Flask environment variables
export FLASK_APP=app.py
export FLASK_ENV=production


# Start Gunicorn (important changes here too)
# Use eventlet worker class
# And importantly, use module:app format.
gunicorn --worker-class eventlet.wsgi.Input --bind 0.0.0.0:$PORT --workers 3 --threads 8 --timeout 0 app:app