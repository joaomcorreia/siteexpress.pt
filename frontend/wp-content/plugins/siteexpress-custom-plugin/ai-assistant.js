function openChat() {
    document.getElementById("chat_box").style.display = "block";
}

function closeChat() {
    document.getElementById("chat_box").style.display = "none";
}

function sendMessage() {
    const input = document.getElementById("user_input");
    const content = document.getElementById("chat_content");
    const userInput = input.value.trim();

    if (!userInput) {
        return;
    }

    input.value = "";
    content.innerHTML += "<p><b>You:</b> " + userInput + "</p>";

    fetch(siteexpressAiAssistant.restUrl, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: userInput }),
    })
        .then((response) => response.json())
        .then((data) => {
            content.innerHTML += "<p><b>Assistant:</b> " + (data.response || "No response.") + "</p>";
        })
        .catch(() => {
            content.innerHTML += "<p><b>Assistant:</b> Sorry, I didn't understand that.</p>";
        });
}
