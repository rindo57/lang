from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Replace with a strong secret key

# MongoDB Connection
client = MongoClient("mongodb://localhost:27017/")  # Replace with your connection string
db = client["language_exchange"]  # Replace with your database name
users = db["users"]
messages = db["messages"]


# Routes
@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("match"))
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        native_language = request.form["native_language"]
        learning_language = request.form["learning_language"]

        if users.find_one({"username": username}):
            return "Username already exists"

        user_id = users.insert_one({
            "username": username,
            "email": email,
            "password": password,
            "native_language": native_language,
            "learning_language": learning_language
        }).inserted_id

        session["username"] = username
        session["user_id"] = str(user_id)
        return redirect(url_for("match"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = users.find_one({"username": username, "password": password})

        if user:
            session["username"] = username
            session["user_id"] = str(user["_id"])
            return redirect(url_for("match"))

        return "Invalid username or password"

    return render_template("login.html")


@app.route("/match")
def match():
    if "username" not in session:
        return redirect(url_for("index"))

    current_user_id = ObjectId(session["user_id"])
    current_user = users.find_one({"_id": current_user_id})

    matches = []
    for user in users.find({
        "$and": [
            {"_id": {"$ne": current_user_id}},
            {"learning_language": current_user["native_language"]},
            {"native_language": current_user["learning_language"]}
        ]
    }):
        matches.append(user)

    return render_template("match.html", matches=matches)


@app.route("/messages/<recipient_id>", methods=["GET", "POST"])
def messages(recipient_id):
    if "username" not in session:
        return redirect(url_for("index"))

    recipient = users.find_one({"_id": ObjectId(recipient_id)})

    if request.method == "POST":
        content = request.form["content"]
        sender_id = ObjectId(session["user_id"])
        message_id = messages.insert_one({
            "sender_id": sender_id,
            "recipient_id": ObjectId(recipient_id),
            "content": content,
            "timestamp": datetime.datetime.utcnow()
        }).inserted_id

        return redirect(url_for("messages", recipient_id=recipient_id))

    messages_list = []
    for message in messages.find({
        "$or": [
            {"sender_id": ObjectId(session["user_id"]), "recipient_id": ObjectId(recipient_id)},
            {"sender_id": ObjectId(recipient_id), "recipient_id": ObjectId(session["user_id"])}
        ]
    }):
        sender = users.find_one({"_id": message["sender_id"]})
        messages_list.append({
            "sender": sender,
            "content": message["content"],
            "timestamp": message["timestamp"]
        })

    return render_template("messages.html", recipient=recipient, messages=messages_list)

@app.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("user_id", None)
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
