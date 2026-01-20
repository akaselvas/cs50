let socket;

function initSocket() {
    if (!socket) {
        socket = io({
            transports: ['polling', 'websocket'],
            forceNew: true
        });
        
        socket.on('connect', function() {
            console.log('Socket connected');
            startGeneration();
        });

        socket.on('connect_error', function(error) {
            console.error('Connection error:', error);
        });

        socket.on('generation_complete', function(data) {
            document.getElementById('loading-message').style.display = 'none';
            document.getElementById('result-area').style.display = 'block';
            document.getElementById('tarot-reading').innerHTML = data.reading;
        });

        socket.on('generation_error', function(data) {
            console.error('Generation error:', data);
            document.getElementById('loading-message').style.display = 'none';
            document.getElementById('tarot-reading').innerHTML = 'An error occurred while generating your reading. Please try again.';
            document.getElementById('result-area').style.display = 'block';
        });
    }
}

function startGeneration() {
    const intencao = document.getElementById('intencaoData').value;
    const selectedCards = document.getElementById('selectedCardsData').value;
    let choosedCards = [];
    
    try {
        const choosedCardsData = document.getElementById('choosedCardsData').value;
        if (choosedCardsData && choosedCardsData.trim() !== '') {
            choosedCards = JSON.parse(choosedCardsData);
        }
    } catch (error) {
        console.error('Error parsing choosed cards:', error);
    }

    console.log('Sending data:', { intencao, selected_cards: selectedCards, choosed_cards: choosedCards });

    socket.emit('start_generation', {
        intencao: intencao,
        selected_cards: selectedCards,
        choosed_cards: choosedCards,
    });
}


function initializeSocket() {
    socket = io({ transports: ['websocket'] });

    

    // DOM elements
    const contentWrapper = document.getElementById('content-wrapper');
    const resultArea = document.getElementById('result-area');
    const shadowOverlay = document.getElementById('shadow-overlay');
    const scrollIndicator = document.getElementById('scroll-indicator');
    const chatInterface = document.getElementById('chat-interface');
    const chatOverlay = document.getElementById('chat-overlay');
    const openChatButton = document.getElementById('open-chat');
    const closeChatButton = document.getElementById('close-chat');
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendMessageButton = document.getElementById('send-message');

    let tarotReading = '';
    let isFirstChatOpen = true;


    // Handle generation complete
    socket.on('generation_complete', function(data) {
        document.getElementById('loading-message').style.display = 'none';
        resultArea.style.display = 'block';
        document.getElementById('tarot-reading').innerHTML = data.reading;
        tarotReading = data.reading;
        
        setTimeout(checkContentOverflow, 40000);
    });

    function checkContentOverflow() {
        if (resultArea.scrollHeight > contentWrapper.clientHeight) {
            showScrollIndicators();
        } else {
            hideScrollIndicators();
        }
    }

    function showScrollIndicators() {
        shadowOverlay.style.display = 'block';
        scrollIndicator.style.display = 'block';
    }

    function hideScrollIndicators() {
        shadowOverlay.style.display = 'none';
        scrollIndicator.style.display = 'none';
    }

    function isAtBottom() {
        const scrollTop = contentWrapper.scrollTop;
        const scrollHeight = contentWrapper.scrollHeight;
        const clientHeight = contentWrapper.clientHeight;
        const tolerance = 5; // pixels of tolerance

        return scrollTop + clientHeight >= scrollHeight - tolerance;
    }

    contentWrapper.addEventListener('scroll', function() {
        if (isAtBottom()) {
            hideScrollIndicators();
        } else if (resultArea.scrollHeight > contentWrapper.clientHeight) {
            showScrollIndicators();
        }
    });

    window.addEventListener('resize', checkContentOverflow);

    openChatButton.addEventListener('click', () => {
        chatInterface.style.display = 'flex';
        chatOverlay.style.display = 'block';
        
        if (isFirstChatOpen) {
            addMessage('bot', 'Olá, vamos conversar mais sobre sua leitura, o que você quer saber?');
            isFirstChatOpen = false;
        }
    });

    closeChatButton.addEventListener('click', () => {
        chatInterface.style.display = 'none';
        chatOverlay.style.display = 'none';
    });

    sendMessageButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    function sendMessage() {
        const message = userInput.value.trim();
        if (message) {
            addMessage('user', message);
            showLoadingIndicator();
            socket.emit('send_message', { message: message, tarot_reading: tarotReading });
            userInput.value = '';
        }
    }

    socket.on('receive_message', (data) => {
        removeLoadingIndicator();
        addMessage('bot', data.message);
    });

    function showLoadingIndicator() {
        const loadingDiv = document.createElement('div');
        loadingDiv.classList.add('chat-message', 'bot-message');
        loadingDiv.innerHTML = `
            <div class="chat-message-content">
                <span class="loading-dots">
                    .<span>.</span><span>.</span><span>.</span>
                </span>
            </div>
        `;
        chatMessages.appendChild(loadingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function removeLoadingIndicator() {
        const loadingIndicator = chatMessages.querySelector('.chat-message:last-child');
        if (loadingIndicator && loadingIndicator.querySelector('.loading-dots')) {
            loadingIndicator.remove();
        }
    }

    function addMessage(sender, content) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('chat-message', sender === 'user' ? 'user-message' : 'bot-message');
        
        // Parse markdown for bot messages
        if (sender === 'bot' && typeof marked !== 'undefined') {
            content = marked.parse(content);
        }
        
        messageDiv.innerHTML = `<div class="chat-message-content">${content}</div>`;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Make startGeneration globally accessible
    window.startGeneration = startGeneration;

}

// Call this function after all scripts have loaded
// document.addEventListener('DOMContentLoaded', function () {
//     const intencao = document.getElementById('intencaoData').value;
//     const selectedCards = document.getElementById('selectedCardsData').value;
//     const choosedCards = JSON.parse(document.getElementById('choosedCardsData').value);

//     initSocket();
//     startGeneration(intencao, selectedCards, choosedCards);
// });
document.addEventListener('DOMContentLoaded', initSocket);