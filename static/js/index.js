document.addEventListener('DOMContentLoaded', function() {
    const botoes = document.querySelectorAll('.botao-personalizado');
    const selectedCardsInput = document.getElementById('selectedCards');
    
    botoes.forEach(botao => {
        botao.addEventListener('click', () => {
            botoes.forEach(b => {
                b.classList.remove('active');
                b.style.opacity = '0.5';
                b.disabled = true;
            });
            botao.classList.add('active');
            botao.style.opacity = '1';
            botao.disabled = false;
            selectedCardsInput.value = botao.dataset.value;
        });
    });
    
    document.getElementById('tarotForm').addEventListener('submit', function (e) {
        if (!selectedCardsInput.value) {
            e.preventDefault();
            alert('Por favor, selecione o número de cartas antes de continuar.');
        }
    });
});