const socket = io();

// Retrieve user details from localStorage (for cross-device persistence)
const name = localStorage.getItem("name");
const room_code = localStorage.getItem("room_code");

// Automatically join room if data exists
if (name && room_code) {
    socket.emit("join", { name, room_code });
}

// Handle form submission for sending messages
document.getElementById("message-form").addEventListener("submit", function (e) {
    e.preventDefault();
    const messageInput = document.getElementById("message-input");
    const message = messageInput.value.trim();

    if (message !== "") {
        socket.emit("send_message", { name, room_code, message });
        messageInput.value = "";
    }
});

// Join the room when the user enters
function joinRoom(userName, userRoom) {
    if (!userName || !userRoom) {
        alert("Name and Room Code are required!");
        return;
    }

    // Store details in localStorage for cross-device access
    localStorage.setItem("name", userName);
    localStorage.setItem("room_code", userRoom);

    socket.emit("join", { name: userName, room_code: userRoom });
}

// Handle incoming messages
socket.on("message", function (data) {
    const messagesContainer = document.getElementById("messages");
    const messageElement = document.createElement("div");

    if (data.name === "System") {
        messageElement.classList.add("system-message");
    } else {
        messageElement.classList.add("user-message");
    }

    messageElement.innerHTML = `<strong>${data.name}:</strong> ${data.msg} <span class="timestamp">${data.timestamp}</span>`;
    messagesContainer.appendChild(messageElement);

    // Auto-scroll to latest message
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
});

// Handle user leaving the room
function leaveRoom() {
    socket.emit("leave", { name, room_code });

    // Clear localStorage to reset session
    localStorage.removeItem("name");
    localStorage.removeItem("room_code");

    window.location.href = "/";
}
