document.addEventListener('DOMContentLoaded', function () {
    const cards = document.querySelectorAll('.card');
    const containerBotoes = document.querySelector('.container-botoes-cartas');
    const leituraButton = document.querySelector('.botao-texto-grande');
    const selectedCardsCount = parseInt(document.getElementById('selectedCardsCount').value);
    let clickedCards = 0;
    let selectedCardsData = [];

    cards.forEach(card => {
        card.addEventListener('click', () => {
            if (card.classList.contains('clicked') || clickedCards >= selectedCardsCount) {
                return;
            }
            const imageUrl = card.getAttribute('data-image');
            const cardName = card.getAttribute('data-name');
            const cardValue = card.getAttribute('data-value');
            const animationDuration = 1000;
            card.style.transition = `transform ${animationDuration}ms ease`;
            if (cardValue === 'invertido') {
                card.style.transform = "rotateX(180deg)";
            } else {
                card.style.transform = "rotateY(180deg)";
            }
            setTimeout(() => {
                card.style.backgroundImage = `url(${imageUrl})`;
                card.classList.add('clicked');
                clickedCards++;
                selectedCardsData.push({ name: cardName, value: cardValue });
                if (clickedCards === selectedCardsCount) {
                    containerBotoes.style.display = 'block';
                    disableUnselectedCards();
                }
            }, animationDuration / 3);
        });
    });

    function disableUnselectedCards() {
        cards.forEach(card => {
            if (!card.classList.contains('clicked')) {
                card.classList.add('disabled');
            }
        });
    }

    leituraButton.addEventListener('click', function (e) {
        e.preventDefault();
        submitChosenCards(selectedCardsData);
    });

    function submitChosenCards(chosenCards) {
        // Update the hidden input with the chosen cards data
        document.getElementById('choosedCards').value = JSON.stringify(chosenCards);

        fetch('/cartas', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.getElementById('csrfToken').value
            },
            body: JSON.stringify({ choosed_cards: chosenCards })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = document.getElementById('resultsUrl').value;
                
                // Add the choosed_cards input
                const choosedCardsInput = document.createElement('input');
                choosedCardsInput.type = 'hidden';
                choosedCardsInput.name = 'choosed_cards';
                choosedCardsInput.value = JSON.stringify(chosenCards);
                form.appendChild(choosedCardsInput);

                // Add the selected_cards_data input
                const dataInput = document.createElement('input');
                dataInput.type = 'hidden';
                dataInput.name = 'selected_cards_data';
                dataInput.value = JSON.stringify(selectedCardsData);
                form.appendChild(dataInput);

                // CSRF Token
                const csrfInput = document.createElement('input');
                csrfInput.type = 'hidden';
                csrfInput.name = 'csrf_token';
                csrfInput.value = document.getElementById('csrfToken').value;
                form.appendChild(csrfInput);

                document.body.appendChild(form);
                form.submit();
            } else {
                console.error('Error submitting chosen cards');
            }
        })
        .catch(error => console.error('Error:', error));
    }
});