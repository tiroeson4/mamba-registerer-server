from flask import Flask, request, jsonify
import json
import os
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# === JSONBin config ===
JSONBIN_ID = os.getenv("JSONBIN_ID")  # берём из переменных окружения
JSONBIN_KEY = os.getenv("JSONBIN_KEY")

if not JSONBIN_ID or not JSONBIN_KEY:
  raise RuntimeError("JSONBIN_ID or JSONBIN_KEY is not set in environment")

JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}"

HEADERS = {
    "X-Master-Key": JSONBIN_KEY,
    "Content-Type": "application/json"
}

# ---- вспомогательные функции ----
def read_config():
    """Читает текущий конфиг из JSONBin"""
    res = requests.get(JSONBIN_URL, headers=HEADERS)
    res.raise_for_status()
    return res.json()["record"]

def write_config(new_data):
    """Перезаписывает конфиг в JSONBin целиком"""
    res = requests.put(JSONBIN_URL, headers=HEADERS, json=new_data)
    res.raise_for_status()
    return res.json()

# ---- API ----

@app.route("/config", methods=["GET"])
def get_config():
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
        "positions": conf.get("positions", {}),
        "cities": conf.get("cities", {})
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

@app.route("/save-position", methods=["POST"])
def save_position():
    data = request.json
    if not data or "browser_id" not in data:
        return jsonify({"error": "Missing browser_id"}), 400

    conf = read_config()

    if "positions" not in conf or not isinstance(conf["positions"], dict):
        conf["positions"] = {}

    conf["positions"][data["browser_id"]] = {
        "top": float(data.get("top", 15)),
        "left": float(data.get("left", 15))
    }

    try:
        write_config(conf)
        print(f"💾 Позиция сохранена: {data['browser_id']} {conf['positions'][data['browser_id']]}")
        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"⚠️ Ошибка сохранения позиции: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/set-cities", methods=["POST"])
def set_cities():
    """Сохраняет список городов для конкретного browser_id"""
    data = request.json or {}
    browser_id = data.get("browser_id")
    cities_text = data.get("cities")

    if not browser_id or not cities_text:
        return jsonify({"error": "Missing browser_id or cities"}), 400

    city_list = [line.strip() for line in cities_text.splitlines() if line.strip()]

    conf = read_config()
    if "cities" not in conf:
        conf["cities"] = {}

    conf["cities"][browser_id] = city_list
    write_config(conf)

    print(f"🌆 Города обновлены для {browser_id}: {city_list}")
    return jsonify({"status": "ok", "count": len(city_list)})


@app.route("/")
def index():
    return "✅ Mamba Registerer server is running!"

# Хранилище задач в памяти (для простоты, можно заменить на JSONBin)
tasks = []
task_status = {}

@app.route("/add_task", methods=["POST"])
def add_task():
    """Добавить задачу для выполнения на ПК"""
    data = request.json
    if not data or "action" not in data:
        return jsonify({"error": "Missing action"}), 400
    
    # Генерируем ID задачи
    task_id = str(int(time.time() * 1000))
    
    task = {
        "id": task_id,
        "action": data["action"],  # "register"
        "times": data.get("times", 1),
        "browser_id": data.get("browser_id", "default"),
        "status": "pending",
        "created_at": time.time()
    }
    
    tasks.append(task)
    task_status[task_id] = {
        "status": "pending",
        "progress": 0,
        "total": task["times"],
        "results": []
    }
    
    print(f"📝 Добавлена задача {task_id}: {task}")
    return jsonify({"status": "ok", "task_id": task_id})

@app.route("/get_task", methods=["GET"])
def get_task():
    """Программа на ПК запрашивает задачу"""
    if not tasks:
        return jsonify({"task": None})
    
    task = tasks.pop(0)  # Берем первую задачу из очереди
    print(f"📤 Выдана задача {task['id']} на выполнение")
    return jsonify({"task": task})

@app.route("/update_task", methods=["POST"])
def update_task():
    """Программа на ПК отчитывается о прогрессе"""
    data = request.json
    task_id = data.get("task_id")
    
    if not task_id or task_id not in task_status:
        return jsonify({"error": "Invalid task_id"}), 400
    
    task_status[task_id]["status"] = data.get("status", "processing")
    task_status[task_id]["progress"] = data.get("progress", 0)
    
    if "result" in data:
        task_status[task_id]["results"].append(data["result"])
    
    print(f"📊 Обновлен статус задачи {task_id}: {task_status[task_id]['progress']}/{task_status[task_id]['total']}")
    return jsonify({"status": "ok"})

@app.route("/task_status/<task_id>", methods=["GET"])
def get_task_status(task_id):
    """Бот или пользователь проверяет статус задачи"""
    if task_id not in task_status:
        return jsonify({"error": "Task not found"}), 404
    
    return jsonify(task_status[task_id])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)

