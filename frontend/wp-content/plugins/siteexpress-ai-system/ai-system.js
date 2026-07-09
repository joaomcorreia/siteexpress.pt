function siteexpressAiSystemOpenChat() {
    const chat = document.getElementById("siteexpress_ai_system_chat");
    if (chat) {
        chat.style.display = "block";
    }
}

function siteexpressAiSystemSendMessage() {
    const input = document.getElementById("siteexpress_ai_system_input");
    const messages = document.getElementById("siteexpress_ai_system_messages");

    if (!input || !messages) {
        return;
    }

    const userInput = input.value.trim();
    if (!userInput) {
        return;
    }

    input.value = "";
    messages.innerHTML += "<p><strong>You:</strong> " + userInput + "</p>";

    fetch(siteexpressAiSystem.restUrl, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: userInput }),
    })
        .then((response) => response.json())
        .then((data) => {
            messages.innerHTML += "<p><strong>Assistant:</strong> " + (data.response || "No response.") + "</p>";
        })
        .catch(() => {
            messages.innerHTML += "<p><strong>Assistant:</strong> Sorry, I encountered an error.</p>";
        });
}
