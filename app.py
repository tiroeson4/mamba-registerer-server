from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

from flask_cors import CORS
CORS(app)

CONFIG_FILE = "settings.json"
LOCAL_FILE = "settings.local.json"


# если файла нет — создаём дефолтный
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
    """Читает глобальный конфиг + подмешивает локальный default если есть"""
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


@app.route("/local-default", methods=["GET"])
def get_local_default():
    """Возвращает локальный default, если есть"""
    if not os.path.exists(LOCAL_FILE):
        return jsonify({"default": None})
    try:
        with open(LOCAL_FILE, "r", encoding="utf-8") as f:
            local = json.load(f)
            return jsonify({"default": local.get("default")})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/local-default", methods=["POST"])
def set_local_default():
    """Сохраняет локальный default (только на этом ПК)"""
    data = request.json or {}
    default_pid = data.get("default")

    if not default_pid:
        return jsonify({"error": "No default provided"}), 400

    with open(LOCAL_FILE, "w", encoding="utf-8") as f:
        json.dump({"default": default_pid}, f, ensure_ascii=False, indent=2)

    return jsonify({"status": "ok", "default": default_pid})


@app.route("/profile/<pid>", methods=["GET"])
def get_profile(pid):
    conf = read_config()
    prof = conf["profiles"].get(pid)
    if not prof:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify(prof)


@app.route("/profile/<pid>", methods=["POST"])
def update_profile(pid):
    conf = read_config()
    body = request.json or {}
    if pid not in conf["profiles"]:
        conf["profiles"][pid] = {}
    conf["profiles"][pid].update(body)
    write_config(conf)
    return jsonify({"status": "ok", "profile": conf["profiles"][pid]})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
