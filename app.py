from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

from flask_cors import CORS
CORS(app)

LOCAL_FILE = "settings.local.json"
CONFIG_FILE = "settings.json"

# если файла нет — создаём с дефолтными значениями
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
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if os.path.exists(LOCAL_FILE):
        with open(LOCAL_FILE, "r", encoding="utf-8") as f:
            local = json.load(f)
            # локальный default перекрывает общий
            if "default" in local:
                data["default"] = local["default"]
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
    import os

    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)

