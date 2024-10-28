import json
import logging
import os
import random
import secrets
from typing import Any, Dict, List, Optional
import google.generativeai as genai
import markdown
import redis
import bleach
import threading

from datetime import timedelta
from dotenv import load_dotenv
from flask import (Flask, flash, redirect, render_template, request,
                   session, url_for, g, jsonify)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_session import Session
from flask_socketio import SocketIO, emit
from flask_talisman import Talisman
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from flask_wtf.csrf import CSRFError
from flask_wtf.csrf import generate_csrf
from flask_wtf.csrf import validate_csrf
from wtforms import Form, StringField, HiddenField

from wtforms.validators import ValidationError  # You need this import for handling CSRF errors


from markupsafe import Markup



# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="gevent")  # Use gevent for WebSockets

# Enhanced security configurations
app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY', secrets.token_urlsafe(32)),
    SESSION_TYPE='redis',
    SESSION_PERMANENT=False,
    SESSION_USE_SIGNER=True,
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',  # Changed from 'Lax' to 'Strict'
    SESSION_COOKIE_NAME='session',
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
    WTF_CSRF_TIME_LIMIT=1800,
    WTF_CSRF_SSL_STRICT=False,
    WTF_CSRF_ENABLED=True,
    WTF_CSRF_METHODS=['POST', 'PUT', 'PATCH', 'DELETE']  # Explicitly specify methods
)


# Redis configuration
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
app.config['SESSION_REDIS'] = redis.from_url(redis_url)


# Initialize Redis client
redis_client = redis.Redis.from_url(redis_url)

# Initialize extensions
csrf = CSRFProtect(app)
Session(app)
limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri=redis_url,
    storage_options={"socket_connect_timeout": 30},
    strategy="fixed-window",
    default_limits=["400 per day", "100 per hour"]
)


csp={
    'default-src': "'self'",
    'style-src': [
        "'self'",
        "'unsafe-inline'",
        "https://fonts.googleapis.com",
        "https://fonts.gstatic.com",
    ],
    'script-src': [
        "'self'",
        "'unsafe-inline'",
        "'unsafe-eval'",
        "https://cdnjs.cloudflare.com",
    ],
    'font-src': [
        "'self'",
        "https://fonts.googleapis.com",
        "https://fonts.gstatic.com",
    ],
    'img-src': [
        "'self'",
        "data:",
    ],
    'connect-src': [
        "'self'",
        "wss:",
        "ws:",
    ]
}


# Talisman(app)
Talisman(app, content_security_policy=csp)




def sanitize_input(text: str) -> str:
    """Sanitizes user input to prevent XSS attacks."""
    allowed_tags = ['a', 'b', 'i', 'em', 'strong', 'p', 'br', 'ul', 'li', 'ol', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'pre', 'code'] # Example allowed tags – adjust as needed
    allowed_attributes = {'a': ['href', 'rel'], 'img': ['src', 'alt']} # Example allowed attributes – adjust as needed
    cleaned_text = bleach.clean(text, tags=allowed_tags, attributes=allowed_attributes, strip=True)
    return cleaned_text

# Utility functions
def markdown_to_html(text: str) -> Markup:
    return Markup(markdown.markdown(text, extensions=['fenced_code', 'codehilite']))


# CSRF error handler
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Handle AJAX requests
        return jsonify({
            'error': 'CSRF token validation failed. Please refresh the page.',
            'success': False
        }), 400
    else:
        # Handle regular form submissions
        flash('Security token has expired. Please try again.', 'error')
        return redirect(url_for('home'))


@app.before_request
def before_request():
    g.nonce = secrets.token_hex(16)
    if 'csrf_token' not in session:
        session['csrf_token'] = generate_csrf()


# @app.after_request
# def refresh_csrf(response):
#     if 'text/html' in response.headers.get('Content-Type', ''):
#         # Set a specific expiration time
#         response.set_cookie(
#             'csrf_token',
#             generate_csrf(),
#             secure=False,
#             httponly=False,
#             samesite='Lax',  # Changed from 'Lax' to 'Strict'
#             max_age=1800,
#             domain=None,  # Explicitly set domain to None
#             path='/'      # Explicitly set path
#         )
#     return response

# Add a new route to check CSRF token status
@app.route('/check_csrf')
def check_csrf():
    csrf_token = session.get('csrf_token')
    cookie_token = request.cookies.get('csrf_token')
    return jsonify({
        'session_token': bool(csrf_token),
        'cookie_token': bool(cookie_token)
    })

# API key handling
api_key = os.getenv("GENAI_API_KEY")
if not api_key:
    raise EnvironmentError("Missing GENAI_API_KEY environment variable.")

# Model initialization
genai.configure(api_key=api_key)
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 30,
    "max_output_tokens": 8192,
}
model = genai.GenerativeModel(
    model_name="gemini-1.5-pro-002",
    generation_config=generation_config
)



# Cache for tarot cards
TAROT_CARDS: List[Dict[str, str]] = [
        {"image": "/static/img/a01.jpg", "name": "O Mago"},
        {"image": "/static/img/a02.jpg", "name": "A Papisa"},
        {"image": "/static/img/a03.jpg", "name": "A Imperatriz"},
        {"image": "/static/img/a04.jpg", "name": "O Imperador"},
        {"image": "/static/img/a05.jpg", "name": "O Papa"},
        {"image": "/static/img/a06.jpg", "name": "Os Namorados"},
        {"image": "/static/img/a07.jpg", "name": "O Carro"},
        {"image": "/static/img/a08.jpg", "name": "A Justiça"},
        {"image": "/static/img/a09.jpg", "name": "O Eremita"},
        {"image": "/static/img/a10.jpg", "name": "A Roda da Fortuna"},
        {"image": "/static/img/a11.jpg", "name": "A Força"},
        {"image": "/static/img/a12.jpg", "name": "O Enforcado"},
        {"image": "/static/img/a13.jpg", "name": "Morte"},
        {"image": "/static/img/a14.jpg", "name": "A Temperança"},
        {"image": "/static/img/a15.jpg", "name": "O Diabo"},
        {"image": "/static/img/a16.jpg", "name": "A Torre"},
        {"image": "/static/img/a17.jpg", "name": "A Estrela"},
        {"image": "/static/img/a18.jpg", "name": "A Lua"},
        {"image": "/static/img/a19.jpg", "name": "O Sol"},
        {"image": "/static/img/a20.jpg", "name": "O Julgamento"},
        {"image": "/static/img/a21.jpg", "name": "O Mundo"},
        {"image": "/static/img/a22.jpg", "name": "O Louco"},
    ]

class TarotForm(FlaskForm):  # Inherit from FlaskForm
    intencao = StringField('Intenção')
    selectedCards = HiddenField('Selected Cards')

# Routes
@app.route('/')
def index():
    form = TarotForm()
    return render_template('index.html', form=form)


@app.route('/get_csrf')
def get_csrf():
    csrf_token = generate_csrf()
    return jsonify({'csrf_token': csrf_token})

@app.route('/process_form', methods=['POST'])
def process_form():
    form = TarotForm(request.form)
    if form.validate_on_submit():
        selected_cards = form.selectedCards.data
        intencao = form.intencao.data
        # Process 'intencao' and 'selected_cards' as needed
        # Redirect to 'cartas' after successful form submission
        return jsonify({'redirect': url_for('cartas')}) 
    return jsonify({'error': 'Form validation failed or CSRF tokens do not match.'}), 400


@app.route('/cartas')
def cartas():
    selected_cards = session.get('selected_cards', 0)

    shuffled_cards = random.sample(TAROT_CARDS, len(TAROT_CARDS))
    for card in shuffled_cards:
        card["value"] = random.choice(["invertido", "normal"])

    cards_group1 = shuffled_cards[:7]
    cards_group2 = shuffled_cards[7:15]
    cards_group3 = shuffled_cards[15:]



    return render_template('cartas.html', cards_group1=cards_group1, cards_group2=cards_group2, cards_group3=cards_group3, selected_cards=selected_cards) 


@app.route('/results', methods=['POST'])
@limiter.limit("5 per minute")
def results():
    intencao = session.get('intencao', '')
    selected_cards = session.get('selected_cards', '')
    selected_cards_data = request.form.get('selected_cards_data')

    try:
        choosed_cards = json.loads(selected_cards_data) if selected_cards_data else []
    except json.JSONDecodeError:
        choosed_cards = []

    logging.info(f"Choosed Cards Data: {selected_cards_data}")

    print(f"Cartas escolhidas: {choosed_cards}")

    return render_template('results.html', intencao=intencao, selected_cards=selected_cards, choosed_cards=choosed_cards)

# SocketIO event handlers
# @socketio.on('start_generation')
# def handle_generation(data: Dict[str, Any]):
#     intencao = data.get('intencao', '')
#     selected_cards = data.get('selected_cards', '')
#     choosed_cards = data.get('choosed_cards', [])

#     reading_html = generate_tarot_reading(intencao, selected_cards, choosed_cards)
#     emit('generation_complete', {'reading': reading_html})

@socketio.on('start_generation')
def handle_generation(data):
    csrf_token = data.get('csrf_token')  # Safely get the csrf_token from the data

    if not csrf_token:
        emit('generation_error', {'message': 'CSRF token missing.'}) # Emit an error event
        return

    try:
        validate_csrf(csrf_token) # Validate the token
    except ValidationError as e:  # Catch validation errors
        emit('generation_error', {'message': str(e)}) # Emit an error event
        return

    intencao = data.get('intencao', '')
    selected_cards = data.get('selected_cards', '')
    choosed_cards = data.get('choosed_cards', [])
    reading_html = generate_tarot_reading(intencao, selected_cards, choosed_cards)

    print(f"CSRF Token: {csrf_token}")  # Now it will only print if csrf_token is defined

    emit('generation_complete', {'reading': reading_html})



@socketio.on('send_message')
def handle_message(data: Dict[str, str]):
    message = sanitize_input(data['message'])
    tarot_reading = data.get('tarot_reading', '')

    try:
        chat_prompt = (
            f"Contexto: Uma leitura de tarô foi realizada com o seguinte resultado:\n\n"
            f"{tarot_reading}\n\nIntencao do usuário {message}\n\n"
            f"Por favor, forneça uma resposta com base neste contexto:"
        )
        response = model.generate_content(chat_prompt)  # Assign the value here!
        emit('receive_message', {'message': response.text})
    except Exception as e:
        logging.error(f"Error in message generation: {str(e)}")
        emit('receive_message', {'message': "An error occurred while processing your request. Please try again later."})

def generate_tarot_reading(intencao: str, selected_cards: str, choosed_cards: List[Dict[str, str]]) -> str:
    prompt = f"Faça leitura do Tarot. A intenção do usuário é: {intencao}. O usuario tirou {selected_cards} cartas. As cartas tiradas são: {json.dumps(choosed_cards, ensure_ascii=False)}"

    try:
        response = model.generate_content(prompt)  # Assign the result of predict() to response
        reading = response.text or "Unable to generate reading." 
    except Exception as e:
        logging.error(f"Error in tarot reading generation: {str(e)}")
        reading = "We're sorry, but we couldn't generate your tarot reading at this time. Please try again later."

    return markdown_to_html(reading)

if __name__ == "__main__":
    socketio.run(app, debug=True)