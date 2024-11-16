import eventlet
eventlet.monkey_patch()  # This is the crucial line!

from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit, join_room
from markupsafe import Markup
import markdown
import os
import google.generativeai as genai
import random
import json
import secrets
from dotenv import load_dotenv
import threading
import redis
from flask_session import Session

app = Flask(__name__)
socketio = SocketIO(app, manage_session=False, message_queue='redis://red-cscpbjpu0jms73fah6rg:6379') # Use message queue for Redis
load_dotenv()

# Session configuration using Redis
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.from_url('redis://red-cscpbjpu0jms73fah6rg:6379') # Your Redis connection URL
app.config['SESSION_PERMANENT'] = False  # If you want sessions to persist after browser close, set to True
app.config['SESSION_USE_SIGNER'] = True  # Recommended for security
app.config['SESSION_COOKIE_SECURE'] = True # Set to True for HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True # Set to True for better security
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax' # Adjust as needed for your requirements

server_session = Session(app) # Initialize the server-side session

# Session secret key
app.secret_key = secrets.token_urlsafe(32)

# Load API key from environment variables
api_key = os.getenv("GENAI_API_KEY")
if not api_key:
    raise EnvironmentError("Missing GENAI_API_KEY environment variable.")
genai.configure(api_key=api_key)

# Model initialization
def create_model():
    generation_config = {
      "temperature": 1,
      "top_p": 0.95,
      "top_k": 30,
      "max_output_tokens": 8192,
      "response_mime_type": "text/plain",
    }
    return genai.GenerativeModel(
        model_name="gemini-1.5-pro-002",
        generation_config=generation_config
    )

model = create_model()

# Convert markdown text to HTML safely
def markdown_to_html(text):
    return Markup(markdown.markdown(text, extensions=['fenced_code', 'codehilite']))

# Home page route
@app.route('/')
def home():
    return render_template('index.html')

# Process the form submission
@app.route('/process_form', methods=['POST'])
def process_form():
    intencao = request.form.get('intencao')
    selected_cards = request.form.get('selectedCards')

    with app.app_context(): # Important: Use app context
        session['intencao'] = intencao  # Store directly in the session
        session['selected_cards'] = selected_cards
        session.modified = True  # Essential: Mark the session as modified

        server_session.save_session(session) # Save the Flask session to Redis

    return redirect(url_for('cartas'))  # Correct redirect

# Display cards
@app.route('/cartas')
def cartas():
    try:
        selected_cards = int(session.get('selected_cards'))
    except (TypeError, ValueError):
        return redirect(url_for('home'))

    # List of cards (this could be loaded from a JSON file or database)
    cards = [
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

    # Assign random orientation to each card
    for card in cards:
        card["value"] = random.choice(["invertido", "normal"])

    random.shuffle(cards)

    # Split the cards into groups for display
    cards_group1 = cards[:7]
    cards_group2 = cards[7:15]
    cards_group3 = cards[15:]

    return render_template(
        'cartas.html', 
        cards_group1=cards_group1, 
        cards_group2=cards_group2, 
        cards_group3=cards_group3, 
        selected_cards=selected_cards,
        )

# Handle tarot reading results
@app.route('/results', methods=['POST'])
def results():
    if 'flask_session_id' not in session:  # Check and redirect EARLY
            print("Error: flask_session_id not found in results route.")
            return redirect(url_for('home'))
    with app.app_context():  # Absolutely required for server-side session access
        session_data = server_session.load_session(session) 

        if not session_data or not all(key in session_data for key in ['intencao', 'selected_cards']):
            print("Error: Incomplete session data in /results.")
            return redirect(url_for('home'))

        intencao = session_data['intencao']
        selected_cards = session_data['selected_cards']
        server_session.delete_session(session)  # Clean up    

    selected_cards_data = request.form.get('selected_cards_data')
    choosed_cards = json.loads(selected_cards_data) if selected_cards_data else []

    return render_template(
        'results.html',
        intencao=intencao,
        selected_cards=selected_cards,
        choosed_cards=choosed_cards,
    )

# Função para gerar a leitura do Tarot em uma thread separada
def generate_tarot_reading(intencao, selected_cards, choosed_cards):
    prompt = f"Faça leitura do Tarot. A intenção do usuário é: {intencao}. O usuario tirou {selected_cards} cartas. As cartas tiradas são: {choosed_cards}"

    try:
        # Solicita o conteúdo gerado pelo modelo
        response = model.generate_content(prompt)
        reading = response.text if response else "Unable to generate reading."
    except Exception as e:
        reading = f"Error generating tarot reading: {str(e)}"
    
    # Retorna o resultado processado como HTML seguro
    return markdown_to_html(reading)


@socketio.on('send_message')
def handle_message(data):
    room = request.sid
    message = data['message']
    tarot_reading = data.get('tarot_reading', '') # Get the reading from the client side

    try:
        chat_prompt = (
            f"Context: A tarot reading was performed with the following result:\n\n"
            f"{tarot_reading}\n\nUser question: {message}\n\n"
            f"Please provide a response based on this context:"
        )
        response = model.generate_content(chat_prompt)
        emit('receive_message', {'message': response.text}, room=room) # corrected.
    except Exception as e:
        emit('receive_message', {'message': f"Error: {str(e)}"}, room=room) # corrected


@socketio.on('connect')
def handle_connect():
    flask_session_id = request.cookies.get('session')

    if flask_session_id:
        with app.app_context():
            session['flask_session_id'] = flask_session_id  # Correct placement
            server_session.save_session(session) # Essential: Save the updated Flask session data.

        room = request.sid
        join_room(room) # Very important for client-specific messaging
        emit('connected', {'data': 'Socket.IO connected'}, room=room) # Confirmation to client
        
    else:
        return False  # Disconnect immediately


@socketio.on('start_generation')  # Decorator corrected
def handle_generation(data):
    if 'flask_session_id' not in session: # Early exit if no flask_session_id, to avoid errors.
        print("Warning: flask_session_id not found in handle_generation")
        emit('session_error', {'message': 'Session not found.'}, room=request.sid)  # Error message to client
        return


    with app.app_context():
        session_data = server_session.load_session(session) # Load the session
        if not session_data or 'intencao' not in session_data or 'selected_cards' not in session_data:  # Handle missing or incomplete session data
            print("Warning: Incomplete session data in handle_generation.")
            emit('session_error', {'message': 'Session data incomplete.'}, room=request.sid) # Consistent error
            return  # Don't proceed

        intencao = session_data.get('intencao')
        selected_cards = session_data.get('selected_cards')

        server_session.delete_session(session) # Clean up session data after it is used.


    choosed_cards = data.get('choosed_cards', [])
    room = request.sid

    def generate_and_emit():
        reading_html = generate_tarot_reading(intencao, selected_cards, choosed_cards)
        socketio.emit('generation_complete', {'reading': reading_html}, room=room)

    threading.Thread(target=generate_and_emit).start()

    # else:
    #     # Handle missing session ID consistently:
    #     print("Warning: Flask session ID not found.") # Logging
    #     emit('session_error', {'message': 'Session ID not found. Please refresh the page.'}, room=request.sid)  # Client-side handling
    #     return  # Stop processing



if __name__ == "__main__":
    app.config['SESSION_COOKIE_SECURE'] = False  # Set to False for local development
    socketio.run(app, debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))