from datetime import datetime
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/")
def home():
    return "<h1>Hello from Flask!</h1><p>This is the home page.</p>"

@app.route("/api/time")
def server_time():
    return jsonify({"server_time": datetime.now().isoformat()})

@app.route("/greet")
def greet():
    name = request.args.get("name", "stranger")
    return f"<h2>Hello, {name}!</h2>"

if __name__ == "__main__":
    app.run(debug=True)
    