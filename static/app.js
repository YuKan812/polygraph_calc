async function sendMessage() {
    const userMessage = document.getElementById('userMessage').value.trim();
    if (!userMessage) return;

    // Добавляем сообщение пользователя в чат
    addMessage(userMessage, 'user');
    document.getElementById('userMessage').value = '';

    // Показываем индикатор загрузки
    addMessage('⏳ Обработка...', 'loading');

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: userMessage })
        });

        // Удаляем индикатор загрузки
        const lastMessage = document.querySelector('.message:last-child');
        if (lastMessage && lastMessage.classList.contains('loading')) {
            lastMessage.remove();
        }

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            addMessage(`Ошибка: ${data.error}`, 'error');
        } else {
            addMessage(data.response, 'assistant');
        }
    } catch (error) {
        // Удаляем индикатор загрузки
        const lastMessage = document.querySelector('.message:last-child');
        if (lastMessage && lastMessage.classList.contains('loading')) {
            lastMessage.remove();
        }
        addMessage(`Ошибка подключения: ${error.message}`, 'error');
    }
}

function addMessage(text, sender) {
    const messagesDiv = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    messageDiv.textContent = text;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Отправка по Enter
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('userMessage').addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && e.ctrlKey) {
            sendMessage();
        }
    });
});
