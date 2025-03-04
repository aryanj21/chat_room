import json
import os
import time
import threading
import sqlite3
import random
import string
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, make_response, jsonify
from flask_socketio import SocketIO, join_room, leave_room, send

# Initialize Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "default_secret_key")  # Use environment variable
socketio = SocketIO(app)

# SQLite Database file
DB_FILE = "chat.db"

# Initialize database
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                room_code TEXT DEFAULT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                room_code TEXT PRIMARY KEY,
                creator TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_code TEXT NOT NULL,
                name TEXT NOT NULL,
                msg TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        conn.commit()

init_db()

# Generate unique room code
def generate_room_code(length=6):
    while True:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=length))
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT room_code FROM rooms WHERE room_code = ?", (code,))
            if not cursor.fetchone():
                return code

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/create-room", methods=["POST"])
def create_room():
    name = request.form.get("name")
    if not name:
        return redirect(url_for("index"))

    # Generate a user_id and store it in a cookie
    user_id = request.cookies.get("user_id")
    if not user_id:
        user_id = "user_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))

    room_code = generate_room_code()

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO rooms (room_code, creator) VALUES (?, ?)", (room_code, name))
        cursor.execute("INSERT OR REPLACE INTO users (user_id, name, room_code) VALUES (?, ?, ?)", (user_id, name, room_code))
        conn.commit()

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

    if not name or not room_code:
        return redirect(url_for("index"))

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT room_code FROM rooms WHERE room_code = ?", (room_code,))
        room_exists = cursor.fetchone()

        if not room_exists:
            return redirect(url_for("index"))  # Room does not exist

        # Retrieve or generate a user ID
        user_id = request.cookies.get("user_id")
        if not user_id:
            user_id = "user_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))

        # Store user details in the database
        cursor.execute("INSERT OR REPLACE INTO users (user_id, name, room_code) VALUES (?, ?, ?)", 
                       (user_id, name, room_code))
        conn.commit()

    # Store user session and set a cookie for cross-device access
    session["name"] = name
    session["room_code"] = room_code
    session.pop("is_creator", None)

    response = make_response(redirect(url_for("chat", room_code=room_code)))
    response.set_cookie("user_id", user_id, max_age=60*60*24*30)  # Store user_id in cookies for 30 days
    return response

@app.route("/chat/<room_code>")
def chat(room_code):
    name = session.get("name")
    if not name:
        return redirect(url_for("index"))

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT creator FROM rooms WHERE room_code = ?", (room_code,))
        room_data = cursor.fetchone()

    if not room_data:
        return redirect(url_for("index"))

    is_creator = (room_data[0] == name)
    return render_template("chat.html", room_code=room_code, name=name, is_creator=is_creator)

@socketio.on("join")
def handle_join(data):
    room_code = data["room_code"]
    name = data["name"]
    join_room(room_code)
    send({"name": "System", "msg": f"{name} joined the room"}, room=room_code)

@socketio.on("send_message")
def handle_message(data):
    room_code = data["room_code"]
    name = data["name"]
    message = data["message"]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (room_code, name, msg, timestamp) VALUES (?, ?, ?, ?)", (room_code, name, message, timestamp))
        conn.commit()

    send({"name": name, "msg": message, "timestamp": timestamp}, room=room_code)

@socketio.on("leave")
def handle_leave(data):
    room_code = data["room_code"]
    name = data["name"]
    leave_room(room_code)
    send({"name": "System", "msg": f"{name} left the room"}, room=room_code)

@app.route("/get-messages/<room_code>")
def get_messages(room_code):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, msg, timestamp FROM messages WHERE room_code = ? ORDER BY id ASC", (room_code,))
        messages = [{"name": row[0], "msg": row[1], "timestamp": row[2]} for row in cursor.fetchall()]
    return jsonify({"messages": messages})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=True)
