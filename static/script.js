const socket = io();
let roomCode = document.getElementById("room-code").innerText;
let userName = document.getElementById("user-name").innerText;

// 🔹 Get user ID from cookies
function getCookie(name) {
    let cookieArr = document.cookie.split(";");
    for (let i = 0; i < cookieArr.length; i++) {
        let cookiePair = cookieArr[i].split("=");
        if (name === cookiePair[0].trim()) {
            return decodeURIComponent(cookiePair[1]);
        }
    }
    return null;
}

let userId = getCookie("user_id");

if (!userId) {
    console.error("User ID not found in cookies! Rejoining may be required.");
}

// 🔹 Function to add messages to chat window
function addMessage(name, message, timestamp) {
    const chatWindow = document.getElementById("chat-window");
    const msgDiv = document.createElement("div");

    msgDiv.classList.add("message");
    if (name === userName) {
        msgDiv.classList.add("own-message");
    }

    msgDiv.innerHTML = `<strong>${name}:</strong> ${message} <span class="timestamp">${timestamp}</span>`;
    chatWindow.appendChild(msgDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight; // Auto-scroll
}

// 🔹 Join room
socket.emit("join", { room_code: roomCode, name: userName, user_id: userId });

// 🔹 Load previous messages
fetch(`/get-messages/${roomCode}`)
    .then(response => response.json())
    .then(data => {
        data.messages.forEach(msg => addMessage(msg.name, msg.msg, msg.timestamp));
    })
    .catch(error => console.error("Error loading messages:", error));

// 🔹 Handle incoming messages
socket.on("message", (data) => {
    addMessage(data.name, data.msg, data.timestamp);
});

// 🔹 Send message
document.getElementById("send-btn").addEventListener("click", function () {
    const messageInput = document.getElementById("message-input");
    const message = messageInput.value.trim();

    if (message !== "") {
        socket.emit("send_message", { room_code: roomCode, message: message, user_id: userId });
        messageInput.value = ""; // Clear input box
    }
});

// 🔹 Leave room (disconnect handling)
window.addEventListener("beforeunload", function () {
    socket.emit("leave", { room_code: roomCode, user_id: userId });
});
