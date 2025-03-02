import json
import os
import time
import threading
import sqlite3
import random
import string
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, make_response
from flask_socketio import SocketIO, join_room, leave_room, send

app = Flask(__name__)
app.config["SECRET_KEY"] = "your_secret_key"
socketio = SocketIO(app)

# SQLite Database file
DB_FILE = "chat.db"

# JSON file to store room data (temporary storage)
ROOMS_FILE = "rooms.json"

# Initialize database
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                room_code TEXT DEFAULT NULL  -- Allow NULL values
            )
        """)
        conn.commit()

init_db()  # Initialize database on startup

# Load rooms from JSON file
def load_rooms():
    if os.path.exists(ROOMS_FILE):
        with open(ROOMS_FILE, "r") as f:
            return json.load(f)
    return {}

# Save rooms to JSON file
def save_rooms(rooms):
    with open(ROOMS_FILE, "w") as f:
        json.dump(rooms, f, indent=4)

rooms = load_rooms()

# Generate unique room code
def generate_room_code(length=6):
    while True:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if code not in rooms:
            return code

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/create-room", methods=["POST"])
def create_room():
    name = request.form.get("name")
    if not name:
        return redirect(url_for("index"))

    user_id = session.get("user_id")
    if not user_id:
        user_id = "user_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        session["user_id"] = user_id  # Store in session

    room_code = generate_room_code()

    # Store user in SQLite with room_code
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO users (user_id, name, room_code) VALUES (?, ?, ?)", 
                       (user_id, name, room_code))
        conn.commit()

    rooms[room_code] = {
        "members": [name],
        "messages": [],
        "creator": name
    }
    save_rooms(rooms)

    session["name"] = name
    session["room_code"] = room_code
    session["is_creator"] = True

    response = make_response(redirect(url_for("chat", room_code=room_code)))
    response.set_cookie("user_id", user_id, max_age=60*60*24*30)  # Store user_id in cookies
    return response

@app.route("/join-room", methods=["POST"])
def join_room_route():
    name = request.form.get("name")
    room_code = request.form.get("room_code")

    if not name or not room_code or room_code not in rooms:
        return redirect(url_for("index"))

    user_id = session.get("user_id")
    if not user_id:
        user_id = "user_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        session["user_id"] = user_id  # Store in session

    # Store user in SQLite with room_code
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO users (user_id, name, room_code) VALUES (?, ?, ?)", 
                       (user_id, name, room_code))
        conn.commit()

    if name not in rooms[room_code]["members"]:
        rooms[room_code]["members"].append(name)
        save_rooms(rooms)

    session["name"] = name
    session["room_code"] = room_code
    session.pop("is_creator", None)  # Remove creator flag
    return redirect(url_for("chat", room_code=room_code))

@app.route("/chat/<room_code>")
def chat(room_code):
    name = session.get("name")
    if not name or room_code not in rooms or name not in rooms[room_code]["members"]:
        return redirect(url_for("index"))

    is_creator = (rooms[room_code]["creator"] == name)
    return render_template("chat.html", room_code=room_code, name=name, is_creator=is_creator)

@socketio.on("join")
def handle_join(data):
    room_code = data["room_code"]
    name = data["name"]

    if room_code in rooms:
        join_room(room_code)
        if name not in rooms[room_code]["members"]:
            rooms[room_code]["members"].append(name)
            save_rooms(rooms)

        send({"name": "System", "msg": f"{name} joined the room"}, room=room_code)

@socketio.on("send_message")
def handle_message(data):
    room_code = data["room_code"]
    name = data["name"]
    message = data["message"]
    timestamp = datetime.now().strftime("%H:%M:%S")

    if room_code in rooms:
        msg_data = {"name": name, "msg": message, "timestamp": timestamp}
        rooms[room_code]["messages"].append(msg_data)
        save_rooms(rooms)

        send(msg_data, room=room_code)

@socketio.on("leave")
def handle_leave(data):
    room_code = data["room_code"]
    name = data["name"]

    if room_code in rooms:
        leave_room(room_code)
        rooms[room_code]["members"].remove(name)
        save_rooms(rooms)

        send({"name": "System", "msg": f"{name} left the room"}, room=room_code)

        if not rooms[room_code]["members"]:
            del rooms[room_code]
            save_rooms(rooms)

# Delete inactive rooms after 30 minutes
def cleanup_rooms():
    while True:
        time.sleep(600)  # Run every 10 minutes
        now = time.time()
        inactive_rooms = []

        for room_code, room in list(rooms.items()):
            if room["messages"]:
                last_message_time = room["messages"][-1].get("timestamp", None)
                if last_message_time:
                    last_message_timestamp = datetime.strptime(last_message_time, "%H:%M:%S").timestamp()
                    if now - last_message_timestamp > 1800:  # 30 minutes
                        inactive_rooms.append(room_code)

        for room_code in inactive_rooms:
            del rooms[room_code]

        save_rooms(rooms)

# Start background cleanup thread
cleanup_thread = threading.Thread(target=cleanup_rooms, daemon=True)
cleanup_thread.start()

if __name__ == "__main__":
    socketio.run(app, debug=True)
