from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)
from flask_cors import CORS
CORS(app)

CONFIG_FILE = "settings.json"

# Если файла нет — создаём дефолтный
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

# ---- вспомогательные функции ----
def read_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def write_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---- API ----

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
        "profiles": conf.get("profiles", {})
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
