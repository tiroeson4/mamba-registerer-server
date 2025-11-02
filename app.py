from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)
from flask_cors import CORS
CORS(app)

CONFIG_FILE = "settings.json"
LOCAL_FILE = "settings.local.json"

# Если нет глобального settings.json — создаём дефолтный
if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "default": "A",
            "profiles": {
                "A": {"name": "Анна", "age": 27},
                "B": {"name": "Мария", "age": 30}
            }
        }, f, ensure_ascii=False, indent=2)


def read_config():
    """Чтение глобального settings.json с подменой локального default"""
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if os.path.exists(LOCAL_FILE):
        try:
            with open(LOCAL_FILE, "r", encoding="utf-8") as f:
                local = json.load(f)
                if "default" in local:
                    data["default"] = local["default"]
        except Exception as e:
            print("⚠️ Ошибка чтения локального файла:", e)
    return data


def write_config(data):
    """Запись глобального settings.json"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.route("/config", methods=["GET"])
def get_config():
    return jsonify(read_config())


@app.route("/config", methods=["POST"])
def update_config():
    data = request.json
    if not data:
        return jsonify({"error": "No data"}), 400
    write_config(data)
    return jsonify({"status": "ok"})


@app.route("/profile/<pid>", methods=["POST"])
def update_profile(pid):
    conf = read_config()
    body = request.json or {}
    if pid not in conf["profiles"]:
        conf["profiles"][pid] = {}
    conf["profiles"][pid].update(body)
    write_config(conf)
    return jsonify({"status": "ok", "profile": conf["profiles"][pid]})


@app.route("/local-default", methods=["GET"])
def get_local_default():
    """Возвращает локальный дефолт"""
    if not os.path.exists(LOCAL_FILE):
        return jsonify({"default": None})
    with open(LOCAL_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return jsonify({"default": data.get("default")})


@app.route("/local-default", methods=["POST"])
def set_local_default():
    """Сохраняет локальный дефолт — только на этом ПК"""
    data = request.json or {}
    if "default" not in data:
        return jsonify({"error": "Missing 'default'"}), 400
    with open(LOCAL_FILE, "w", encoding="utf-8") as f:
        json.dump({"default": data["default"]}, f, ensure_ascii=False, indent=2)
    return jsonify({"status": "ok", "default": data["default"]})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
