from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json

app = Flask(__name__)
CORS(app)

# === JSONBin config ===
JSONBIN_ID = "691330e2ae596e708f527e4c"
JSONBIN_KEY = "$2a$10$gNDyVdYtS5hQ7KoJUKoA6OfTBOXvgoRLWw21WoKorPkb9qIZBB992"

JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}"
HEADERS = {
    "X-Master-Key": JSONBIN_KEY,
    "Content-Type": "application/json"
}


# ---------- Вспомогательные функции ----------

def read_db():
    """Читает текущий конфиг из JSONBin и гарантирует нужные ключи."""
    res = requests.get(JSONBIN_URL, headers=HEADERS)
    res.raise_for_status()
    data = res.json()["record"]

    # Гарантируем наличие всех секций
    data.setdefault("profiles", {})
    data.setdefault("defaults", {})
    data.setdefault("positions", {})
    data.setdefault("pending_city", {})

    return data


def write_db(db):
    """Перезаписывает конфиг в JSONBin целиком."""
    res = requests.put(JSONBIN_URL, headers=HEADERS, json=db)
    res.raise_for_status()
    return res.json()


# ---------- API ДЛЯ JS ----------

@app.route("/config", methods=["GET"])
def get_config():
    db = read_db()
    browser_id = request.args.get("browser_id")

    # Определяем дефолтный профиль для этого browser_id
    defaults = db.get("defaults", {})
    default_pid = defaults.get(browser_id)

    if not default_pid:
        # если не задано явно, пробуем вытащить из названия (profile_B -> B)
        if browser_id and browser_id.startswith("profile_"):
            default_pid = browser_id.split("_", 1)[1]
        else:
            default_pid = "A"

    return jsonify({
        "profiles": db.get("profiles", {}),
        "default": default_pid,
        # JS ждёт positions в формате { "profile_A": {...}, "profile_B": {...} }
        "positions": db.get("positions", {}),
        # Python пишет city_id сюда по browser_id
        "city_id": db.get("pending_city", {}).get(browser_id)
    })


@app.route("/save-position", methods=["POST"])
def save_position():
    data = request.json or {}
    browser_id = data.get("browser_id")

    if not browser_id:
        return jsonify({"error": "browser_id missing"}), 400

    db = read_db()
    db.setdefault("positions", {})
    db["positions"][browser_id] = {
        "top": float(data.get("top", 15)),
        "left": float(data.get("left", 15))
    }

    write_db(db)
    print(f"💾 Позиция сохранена для {browser_id}: {db['positions'][browser_id]}")
    return jsonify({"status": "ok"})


@app.route("/set-default", methods=["POST"])
def set_default():
    """
    Тело:
    {
      "browser_id": "profile_B",
      "default": "B"
    }
    """
    data = request.json or {}
    browser_id = data.get("browser_id")
    default_profile = data.get("default")

    if not browser_id or not default_profile:
        return jsonify({"error": "browser_id or default missing"}), 400

    db = read_db()
    db.setdefault("defaults", {})
    db["defaults"][browser_id] = default_profile

    write_db(db)
    print(f"⭐ Дефолтный профиль для {browser_id}: {default_profile}")
    return jsonify({"status": "ok"})


@app.route("/update-profile", methods=["POST"])
def update_profile():
    """
    Тело:
    {
      "pid": "A",
      "profile": { "name": "Инесса", "age": 28 }
    }
    """
    data = request.json or {}
    pid = data.get("pid")
    profile_data = data.get("profile")

    if not pid or not profile_data:
        return jsonify({"error": "pid or profile missing"}), 400

    db = read_db()
    db.setdefault("profiles", {})
    db["profiles"][pid] = profile_data

    write_db(db)
    print(f"👤 Профиль {pid} обновлён: {profile_data}")
    return jsonify({"status": "ok"})


# ---------- API ДЛЯ PYTHON (city_id) ----------

@app.route("/python/set-city-id", methods=["POST"])
def python_set_city_id():
    """
    Тело:
    {
      "browser_id": "profile_B",
      "city_id": "3159_4891_4917_0"
    }
    """
    data = request.json or {}
    browser_id = data.get("browser_id")
    city_id = data.get("city_id")

    if not browser_id or not city_id:
        return jsonify({"error": "browser_id or city_id missing"}), 400

    db = read_db()
    db.setdefault("pending_city", {})
    db["pending_city"][browser_id] = city_id

    write_db(db)
    print(f"📡 PYTHON → JS: city_id={city_id} для {browser_id}")
    return jsonify({"status": "ok"})


@app.route("/python/clear-city-id", methods=["POST"])
def python_clear_city_id():
    """
    Тело:
    {
      "browser_id": "profile_B"
    }
    """
    data = request.json or {}
    browser_id = data.get("browser_id")

    if not browser_id:
        return jsonify({"error": "browser_id missing"}), 400

    db = read_db()
    if "pending_city" in db and browser_id in db["pending_city"]:
        del db["pending_city"][browser_id]
        write_db(db)
        print(f"🧹 JS → PYTHON: city_id очищен для {browser_id}")

    return jsonify({"status": "ok"})


@app.route("/")
def index():
    return "✅ JSONBin Mamba Registerer server is running!"


if __name__ == "__main__":
    # На Render порт берётся из переменной окружения, локально можно 3000
    import os
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
