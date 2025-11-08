from flask import Flask, request, jsonify, send_file
import json
import os

app = Flask(__name__)
from flask_cors import CORS
CORS(app)

CONFIG_FILE = "settings.json"
CITIES_FILE = "cities.txt"

# ==========================
# 📁 Инициализация settings.json
# ==========================
if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "defaults": {
                "profile_A": "A",
                "profile_B": "B"
            },
            "profiles": {
                "A": {"name": "Анна", "age": 27},
                "B": {"name": "Мария", "age": 30}
            },
            "global_default": "A"
        }, f, ensure_ascii=False, indent=2)


# ==========================
# 🔧 Вспомогательные функции
# ==========================
def read_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def write_config(new_data):
    """Безопасно сохраняет settings.json"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                old_data = json.load(f)
        else:
            old_data = {}

        merged = old_data.copy()
        for k, v in new_data.items():
            if isinstance(v, dict) and isinstance(old_data.get(k), dict):
                merged[k].update(v)
            else:
                merged[k] = v

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("⚠️ Ошибка при записи settings.json:", e)


# ==========================
# 🌐 API
# ==========================

@app.route("/config", methods=["GET"])
def get_config():
    """Отдаёт профиль с учётом browser_id"""
    conf = read_config()
    browser_id = request.args.get("browser_id")
    default_pid = conf.get("global_default", "A")

    if browser_id:
        defaults = conf.get("defaults", {})
        if browser_id in defaults:
            default_pid = defaults[browser_id]

    return jsonify({
        "default": default_pid,
        "profiles": conf.get("profiles", {}),
        "positions": conf.get("positions", {})
    })


@app.route("/set-default", methods=["POST"])
def set_default():
    """Устанавливает дефолтный профиль для конкретного browser_id"""
    data = request.json or {}
    browser_id = data.get("browser_id")
    new_default = data.get("default")

    if not browser_id or not new_default:
        return jsonify({"error": "browser_id or default missing"}), 400

    conf = read_config()
    if "defaults" not in conf:
        conf["defaults"] = {}

    conf["defaults"][browser_id] = new_default
    write_config(conf)

    return jsonify({
        "status": "ok",
        "browser_id": browser_id,
        "default": new_default
    })


@app.route("/profile/<pid>", methods=["POST"])
def update_profile(pid):
    """Обновляет данные конкретного профиля"""
    conf = read_config()
    body = request.json or {}
    if pid not in conf["profiles"]:
        conf["profiles"][pid] = {}
    conf["profiles"][pid].update(body)
    write_config(conf)
    return jsonify({"status": "ok", "profile": conf["profiles"][pid]})


@app.route("/debug", methods=["GET"])
def debug():
    """Отладка — показать текущие defaults и profiles"""
    return jsonify(read_config())


@app.route("/save-position", methods=["POST"])
def save_position():
    """Сохраняет координаты панели для конкретного браузера (browser_id)"""
    data = request.json
    if not data or "browser_id" not in data:
        return jsonify({"error": "Missing browser_id"}), 400

    conf = read_config()

    # если нет ключа "positions", создаём
    if "positions" not in conf or not isinstance(conf["positions"], dict):
        conf["positions"] = {}

    conf["positions"][data["browser_id"]] = {
        "top": float(data.get("top", 15)),
        "left": float(data.get("left", 15))
    }

    # сохраняем
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(conf, f, ensure_ascii=False, indent=2)
        print(f"💾 Позиция сохранена: {data['browser_id']} {conf['positions'][data['browser_id']]}")
        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"⚠️ Ошибка сохранения позиции: {e}")
        return jsonify({"error": str(e)}), 500


# ==========================
# 🏙️ Работа с городами
# ==========================

@app.route("/add-city", methods=["POST"])
def add_city():
    """Добавляет строку 'город - ID (browser_id)' в cities.txt"""
    try:
        data = request.get_json(force=True)
        name = data.get("name")
        location = data.get("location")
        browser_id = data.get("browser_id", "unknown")

        if not name or not location:
            return jsonify({"error": "missing fields"}), 400

        line = f"{name} - {location} ({browser_id})"
        print("📍 Новый город:", line)

        if not os.path.exists(CITIES_FILE):
            open(CITIES_FILE, "w", encoding="utf-8").close()

        with open(CITIES_FILE, "r", encoding="utf-8") as f:
            existing = f.read().splitlines()

        if line in existing:
            return jsonify({"status": "duplicate"}), 200

        with open(CITIES_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print("❌ Ошибка /add-city:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/get-cities", methods=["GET"])
def get_cities():
    """Возвращает список всех сохранённых городов"""
    if not os.path.exists(CITIES_FILE):
        return jsonify({"error": "Файл не найден"}), 404

    with open(CITIES_FILE, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    return jsonify({
        "cities": lines,
        "count": len(lines)
    })


@app.route("/download-cities", methods=["GET"])
def download_cities():
    """Позволяет скачать файл cities.txt"""
    if not os.path.exists(CITIES_FILE):
        return "Файл не найден", 404
    return send_file(CITIES_FILE, as_attachment=True)


@app.route("/clear-cities", methods=["POST"])
def clear_cities():
    """Очищает файл cities.txt"""
    try:
        open(CITIES_FILE, "w", encoding="utf-8").close()
        print("🧹 cities.txt очищен.")
        return jsonify({"status": "cleared"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================
# 🚀 Индекс
# ==========================
@app.route("/")
def index():
    return "✅ Mamba Registerer server is running!"


# ==========================
# 🖥️ Запуск
# ==========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
