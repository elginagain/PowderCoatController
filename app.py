from flask import Flask, render_template, request, jsonify
import os
import json
import time
import threading
from temperature_sensor import read_temperature  # Import the sensor reading function

app = Flask(__name__)

CONFIG_FILE = "config.json"


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "temp_offset": 0.0,
        "pid_tunings": [10, 5, 1],
        "target_temperature": 350,
        "oven_on": False,
        "light_on": False,
        "timer_running": False,
        "time_remaining": 0
    }


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


config = load_config()

# Timer Variables
timer_running = config.get("timer_running", False)
time_remaining = config.get("time_remaining", 0)
timer_start_time = None
timer_lock = threading.Lock()


def timer_thread():
    global time_remaining, timer_running, timer_start_time
    while True:
        with timer_lock:
            if timer_running and time_remaining > 0:
                elapsed = time.time() - timer_start_time
                time_remaining = max(0, time_remaining - elapsed)
                config["time_remaining"] = int(time_remaining)
                save_config(config)
                if time_remaining <= 0:
                    timer_running = False
                    config["timer_running"] = False
                    save_config(config)
            timer_start_time = time.time()
        time.sleep(1)


# Start Timer Background Thread
timer_thread_instance = threading.Thread(target=timer_thread, daemon=True)
timer_thread_instance.start()


@app.route('/')
def dashboard():
    return render_template('dashboard.html')


@app.route('/settings')
def settings():
    return render_template('settings.html')


@app.route('/toggle_light', methods=['POST'])
def toggle_light():
    config["light_on"] = not config.get("light_on", False)
    save_config(config)
    return jsonify({"light_on": config["light_on"]})


@app.route('/power', methods=['POST'])
def toggle_oven():
    config["oven_on"] = not config.get("oven_on", False)
    save_config(config)
    return jsonify({"oven_on": config["oven_on"]})


@app.route('/toggle_timer', methods=['POST'])
def toggle_timer():
    global timer_running, timer_start_time, time_remaining
    with timer_lock:
        if timer_running:
            elapsed = time.time() - timer_start_time
            time_remaining = max(0, time_remaining - elapsed)
            timer_running = False
        else:
            timer_start_time = time.time()
            timer_running = True

        config["timer_running"] = timer_running
        config["time_remaining"] = int(time_remaining)
        save_config(config)

    return jsonify({"timer_running": timer_running, "time_remaining": int(time_remaining)})


@app.route('/set_timer', methods=['POST'])
def set_timer():
    global time_remaining, timer_running
    data = request.get_json()
    with timer_lock:
        time_remaining = data.get("time", 0) * 60  # Convert minutes to seconds
        timer_running = False
        config["timer_running"] = False
        config["time_remaining"] = int(time_remaining)
        save_config(config)

    return jsonify({"time_remaining": int(time_remaining)})


@app.route('/get_timer', methods=['GET'])
def get_timer():
    global timer_running, time_remaining
    return jsonify({"timer_running": timer_running, "time_remaining": int(time_remaining)})


@app.route('/set_temperature', methods=['POST'])
def set_temperature():
    data = request.get_json()
    config["target_temperature"] = data.get("temperature", 350)
    save_config(config)
    return jsonify({"target_temperature": config["target_temperature"]})


@app.route('/get_temperature', methods=['GET'])
def get_temperature():
    return jsonify({"target_temperature": config["target_temperature"]})


# New endpoint: Return current sensor temperature (Fahrenheit)
@app.route('/current_temperature', methods=['GET'])
def current_temperature():
    current_temp = read_temperature()
    return jsonify({"current_temperature": current_temp})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
