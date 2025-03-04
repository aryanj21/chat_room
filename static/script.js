const socket = io();

// 🔹 Ensure room code and username are correctly retrieved
let roomCode = document.getElementById("room-code") ? document.getElementById("room-code").innerText : null;
let userName = document.getElementById("user-name") ? document.getElementById("user-name").innerText : "Anonymous";

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
    console.error("User ID not found in cookies! Assigning temporary ID.");
    userId = "temp_" + Math.random().toString(36).substr(2, 9); // Assign temporary ID
    document.cookie = `user_id=${userId}; path=/`; // Save in cookies
}

// 🔹 Function to add messages to chat window
function addMessage(name, message, timestamp) {
    const chatWindow = document.getElementById("chat-window");
    const msgDiv = document.createElement("div");

    msgDiv.classList.add("message");
    if (name === userName) {
        msgDiv.classList.add("own-message");
    }

    // Format timestamp for better readability
    let timeString = new Date(timestamp).toLocaleTimeString();

    msgDiv.innerHTML = `<strong>${name}:</strong> ${message} <span class="timestamp">${timeString}</span>`;
    chatWindow.appendChild(msgDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight; // Auto-scroll
}

// 🔹 Join room
socket.emit("join", { room_code: roomCode, name: userName, user_id: userId });

// 🔹 Load previous messages from the server
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

// 🔹 Send message function
function sendMessage() {
    const messageInput = document.getElementById("message-input");
    const message = messageInput.value.trim();

    if (message !== "") {
        socket.emit("send_message", { room_code: roomCode, name: userName, message: message, user_id: userId });
        messageInput.value = ""; // Clear input box
    }
}

// 🔹 Event listener for sending messages
document.getElementById("send-btn").addEventListener("click", sendMessage);
document.getElementById("message-input").addEventListener("keypress", function (event) {
    if (event.key === "Enter") {
        sendMessage();
    }
});

// 🔹 Leave room (disconnect handling)
document.getElementById("leave-btn").addEventListener("click", function () {
    socket.emit("leave", { room_code: roomCode, user_id: userId });
    window.location.href = "/";
});

window.addEventListener("beforeunload", function () {
    socket.emit("leave", { room_code: roomCode, user_id: userId });
});
