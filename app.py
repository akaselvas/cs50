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
from rq import Queue
import redis
import threading

app = Flask(__name__)
socketio = SocketIO(app)

load_dotenv()

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

# Redis connection
redis_url = os.environ.get('REDIS_URL', 'redis://red-cscpbjpu0jms73fah6rg:6379')
redis_conn = redis.from_url(redis_url)
q = Queue(connection=redis_conn)  # Create a Redis queue

# Home page route
@app.route('/')
def home():
    return render_template('index.html')

# Process the form submission
@app.route('/process_form', methods=['POST'])
def process_form():
    intencao = request.form.get('intencao')
    selected_cards = request.form.get('selectedCards')

    session['intencao'] = intencao
    session['selected_cards'] = selected_cards
    
    return redirect(url_for('cartas'))

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

    return render_template('cartas.html', cards_group1=cards_group1, cards_group2=cards_group2, cards_group3=cards_group3, selected_cards=selected_cards)

# Handle tarot reading results
@app.route('/results', methods=['POST'])
def results():
    intencao = session.get('intencao', '')
    selected_cards = session.get('selected_cards', '')

    selected_cards_data = request.form.get('selected_cards_data')
    choosed_cards = json.loads(selected_cards_data) if selected_cards_data else []

    # Renderiza a página que vai mostrar a mensagem de carregamento.
    return render_template('results.html', intencao=intencao, selected_cards=selected_cards, choosed_cards=choosed_cards)


# Função para gerar a leitura do Tarot em uma thread separada
def generate_tarot_reading(intencao, selected_cards, choosed_cards):
    prompt = f"Faça leitura do Tarot. A intenção do usuário é: {intencao}. O usuario tirou {selected_cards} cartas. As cartas tiradas são: {choosed_cards}"
    try:
        response = model.generate_content(prompt)
        reading = response.text if response else "Unable to generate reading."
        return markdown_to_html(reading)
    except Exception as e:
        return f"Error generating tarot reading: {str(e)}"

# Função que lida com a geração da leitura via SocketIO
@socketio.on('start_generation')
def handle_generation(data):
    intencao = data.get('intencao', '')
    selected_cards = data.get('selected_cards', '')
    choosed_cards = data.get('choosed_cards', [])
    job = q.enqueue(generate_tarot_reading, intencao, selected_cards, choosed_cards)
    emit('generation_started', {'jobId': job.id}) # Send job ID to client


# New function to handle chat messages
@socketio.on('send_message')
def handle_message(data):
    room = request.sid  # Use request.sid to get the SocketIO session ID
    message = data['message']
    tarot_reading = data.get('tarot_reading', '')

    try:
        chat_prompt = (
            f"Context: A tarot reading was performed with the following result:\n\n"
            f"{tarot_reading}\n\nUser question: {message}\n\n"
            f"Please provide a response based on this context:"
        )
        response = model.generate_content(chat_prompt)
        emit('receive_message', {'message': response.text}, room=room)
    except Exception as e:
        emit('receive_message', {'message': f"Error: {str(e)}"}, room=room)


# Join a room based on the user's session ID
@socketio.on('connect')
def handle_connect():
    room = request.sid  # Each client gets their own room using request.sid
    join_room(room)
    socketio.emit('join', {'message': f'Client {room} connected.'}, room=room)


# Function that emits only to the client's specific room
@socketio.on('start_generation')
def handle_generation(data):
    room = request.sid  # Use request.sid here as well
    intencao = data.get('intencao', '')
    selected_cards = data.get('selected_cards', '')
    choosed_cards = data.get('choosed_cards', [])

    def generate_and_emit():
        reading_html = generate_tarot_reading(intencao, selected_cards, choosed_cards)
        socketio.emit('generation_complete', {'reading': reading_html}, room=room)

    threading.Thread(target=generate_and_emit).start()

@socketio.on('check_job')
def check_job_status(data):
    job_id = data.get('jobId')
    job = q.fetch_job(job_id)
    if job:
        if job.is_finished:
            reading_html = job.result
            emit('generation_complete', {'reading': reading_html})
        elif job.is_failed:
            emit('generation_failed', {'error': job.exc_info})
        else:
            emit('generation_pending') #Tell the client the job is still pending
    else:
        emit('generation_failed', {'error': 'Job not found'})


if __name__ == "__main__":
    socketio.run(app, debug=True)
