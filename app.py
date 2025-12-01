from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess

app = Flask(__name__)
CORS(app)

# Хранилище данных в памяти (можно заменить на файл)
db = {
    "profiles": {},
    "defaults": {},
    "positions": {},
    "pending_city": {}  # Python кладёт сюда city_id
}

# ---------- API ДЛЯ JS ----------

@app.route("/config", methods=["GET"])
def get_config():
    browser_id = request.args.get("browser_id")

    return jsonify({
        "profiles": db["profiles"],
        "default": db["defaults"].get(browser_id),
        "positions": db["positions"].get(browser_id),
        "city_id": db["pending_city"].get(browser_id)  # Python → JS
    })


@app.route("/save-position", methods=["POST"])
def save_position():
    data = request.json
    browser_id = data["browser_id"]

    db["positions"][browser_id] = {
        "top": data["top"],
        "left": data["left"]
    }
    return jsonify({"status": "ok"})


@app.route("/set-default", methods=["POST"])
def set_default():
    data = request.json
    browser_id = data["browser_id"]
    default_profile = data["default"]

    db["defaults"][browser_id] = default_profile
    return jsonify({"status": "ok"})


@app.route("/update-profile", methods=["POST"])
def update_profile():
    data = request.json
    pid = data["pid"]
    profile_data = data["profile"]

    db["profiles"][pid] = profile_data
    return jsonify({"status": "ok"})


# ---------- НОВОЕ: JS → PYTHON (запуск регистрации) ----------

@app.route("/start-registration", methods=["POST"])
def start_registration():
    """JS присылает deep_link, Flask запускает python_script.py"""
    data = request.json
    deep_link = data.get("deep_link")
    browser_id = data.get("browser_id")

    if not deep_link or not browser_id:
        return jsonify({"error": "missing deep_link or browser_id"}), 400

    print(f"🚀 JS → PYTHON: запуск регистрации для {browser_id}")

    # Передаём данные в Python скрипт
    subprocess.Popen([
        "python", "python_worker.py", deep_link, browser_id
    ])

    return jsonify({"status": "started"})


# ---------- API ДЛЯ PYTHON ----------

@app.route("/python/set-city-id", methods=["POST"])
def python_set_city_id():
    data = request.json
    browser_id = data["browser_id"]
    city_id = data["city_id"]

    db["pending_city"][browser_id] = city_id
    print(f"📡 PYTHON → JS: city_id={city_id} для {browser_id}")

    return jsonify({"status": "ok"})


@app.route("/python/clear-city-id", methods=["POST"])
def python_clear_city_id():
    data = request.json
    browser_id = data["browser_id"]

    db["pending_city"].pop(browser_id, None)
    print(f"🧹 JS → PYTHON: city_id очищен для {browser_id}")

    return jsonify({"status": "ok"})


@app.route("/")
def index():
    return "✅ Flask Mamba Registerer is running"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
