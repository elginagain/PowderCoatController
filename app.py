import os
# Do not force the use of /dev/mem so that RPi.GPIO uses /dev/gpiomem.
# os.environ["GPIO_USE_DEV_MEM"] = "1"

from flask import Flask, render_template, request, jsonify
import json
import time
import threading
from datetime import datetime, timedelta
from temperature_sensor import read_temperature  # Your sensor reading function
from db import get_db, init_db  # Database helper functions
import sys

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

# Initialize the database at startup.
init_db()

# Global variable for PWM and SSR pin
pwm = None
SSR_PIN = 17  # GPIO pin for SSR control

# -------------------------
# Function to Initialize GPIO using RPi.GPIO
# -------------------------
def init_gpio():
    global pwm
    if sys.platform.startswith("linux"):
        try:
            import RPi.GPIO as GPIO
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(SSR_PIN, GPIO.OUT)
            # Set up PWM on SSR_PIN at 100Hz.
            pwm = GPIO.PWM(SSR_PIN, 100)
            pwm.start(0)  # Start with 0% duty cycle (heater off)
            print("GPIO initialized successfully.")
        except Exception as e:
            print("Error setting up GPIO:", e)
            pwm = None
    else:
        pwm = None

# -------------------------
# Cycle Management Functions
# -------------------------
current_cycle_id = None

def start_new_cycle():
    global current_cycle_id
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO cycles (start_time) VALUES (?)", (datetime.now(),))
    current_cycle_id = cur.lastrowid
    conn.commit()
    conn.close()
    print(f"Started new cycle, id {current_cycle_id}")
    return current_cycle_id

def end_current_cycle():
    global current_cycle_id
    if current_cycle_id is not None:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE cycles SET end_time = ? WHERE id = ?", (datetime.now(), current_cycle_id))
        conn.commit()
        conn.close()
        print(f"Ended cycle, id {current_cycle_id}")
        current_cycle_id = None
        purge_old_cycles()

def purge_old_cycles():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id FROM cycles
        WHERE end_time IS NOT NULL
        ORDER BY end_time DESC
        LIMIT -1 OFFSET 20
    """)
    rows = cur.fetchall()
    if rows:
        ids = [str(row["id"]) for row in rows]
        placeholders = ",".join("?" for _ in ids)
        cur.execute(f"DELETE FROM readings WHERE cycle_id IN ({placeholders})", ids)
        cur.execute(f"DELETE FROM cycles WHERE id IN ({placeholders})", ids)
        conn.commit()
        print(f"Purged cycles: {ids}")
    conn.close()

# -------------------------
# Background Temperature Logger
# -------------------------
def temperature_logger():
    global current_cycle_id
    while True:
        current_temp = read_temperature()
        print(f"[Logger] current_temp={current_temp}, oven_on={config['oven_on']}, cycle_id={current_cycle_id}")
        if config["oven_on"] and current_cycle_id is not None:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO readings (cycle_id, timestamp, temperature, set_temperature)
                VALUES (?, ?, ?, ?)
            """, (current_cycle_id, datetime.now(), current_temp, config["target_temperature"]))
            conn.commit()
            conn.close()
            print("[Logger] Inserted reading into DB.")
        else:
            print("[Logger] Not logging because oven_off or no active cycle.")
        time.sleep(5)  # Log every 5 seconds for debugging

logger_thread = threading.Thread(target=temperature_logger, daemon=True)
logger_thread.start()

# -------------------------
# Timer Logic
# -------------------------
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

timer_thread_instance = threading.Thread(target=timer_thread, daemon=True)
timer_thread_instance.start()

# -------------------------
# PID Control for SSR Output (using RPi.GPIO)
# -------------------------
Kp = 1.0
Ki = 0.1
Kd = 0.05
integral = 0.0
last_error = 0.0
pid_thread = None

def pid_control_loop():
    global integral, last_error
    last_time = time.time()
    max_integral = 500  # Anti-windup limit
    while config["oven_on"]:
        current_temp = read_temperature()
        setpoint = config["target_temperature"]
        error = setpoint - current_temp
        current_time = time.time()
        dt = current_time - last_time if (current_time - last_time) > 0 else 1

        integral += error * dt
        integral = max(min(integral, max_integral), -max_integral)

        derivative = (error - last_error) / dt
        output = Kp * error + Ki * integral + Kd * derivative
        duty_cycle = max(0, min(100, output))
        print(f"PID: setpoint={setpoint}, current={current_temp:.2f}, error={error:.2f}, duty={duty_cycle:.2f}")
        if pwm is not None:
            print(f"Calling pwm.ChangeDutyCycle({duty_cycle})")
            pwm.ChangeDutyCycle(duty_cycle)
        last_error = error
        last_time = current_time
        time.sleep(1)
    if pwm is not None:
        pwm.ChangeDutyCycle(0)
    print("PID control loop ended.")

# -------------------------
# Routes
# -------------------------
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
    global current_cycle_id, pid_thread
    print("Received /power request")
    config["oven_on"] = not config.get("oven_on", False)
    print(f"Setting oven_on to {config['oven_on']}")
    if config["oven_on"]:
        start_new_cycle()
        if pid_thread is None or not pid_thread.is_alive():
            pid_thread = threading.Thread(target=pid_control_loop, daemon=True)
            pid_thread.start()
    else:
        end_current_cycle()
    save_config(config)
    print(f"Oven status now: {config['oven_on']}")
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
        time_remaining = data.get("time", 0) * 60
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
def set_temperature_endpoint():
    data = request.get_json()
    config["target_temperature"] = data.get("temperature", 350)
    save_config(config)
    return jsonify({"target_temperature": config["target_temperature"]})

@app.route('/get_temperature', methods=['GET'])
def get_temperature_endpoint():
    return jsonify({"target_temperature": config["target_temperature"]})

@app.route('/current_temperature', methods=['GET'])
def current_temperature():
    temp = read_temperature()
    return jsonify({"current_temperature": temp})

@app.route('/temperature_graph')
def temperature_graph():
    return render_template('current_temp_history.html')

# -------------------------
# Modified /current_temp_history Route (No 2-hour filter for diagnosis)
# -------------------------
@app.route('/current_temp_history')
def current_temp_history():
    if current_cycle_id is None:
        now = datetime.now()
        dummy = [{
            "x": int(now.timestamp() * 1000),
            "y_actual": read_temperature(),
            "y_set": config["target_temperature"]
        }]
        print("No active cycle; returning dummy data.")
        return jsonify(dummy)

    conn = get_db()
    cur = conn.cursor()
    # Use 'localtime' modifier to get local timestamps
    cur.execute("""
        SELECT CAST((julianday(timestamp, 'localtime') - 2440587.5)*86400 AS INTEGER) AS ts,
               temperature,
               set_temperature
        FROM readings
        WHERE cycle_id = ?
        ORDER BY timestamp ASC
    """, (current_cycle_id,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        now = datetime.now()
        dummy = [{
            "x": int(now.timestamp() * 1000),
            "y_actual": read_temperature(),
            "y_set": config["target_temperature"]
        }]
        print("No readings found for current cycle; returning dummy data.")
        return jsonify(dummy)

    print(f"current_temp_history: Found {len(rows)} readings for cycle {current_cycle_id}")
    data = []
    for r in rows:
        data.append({
            "x": int(r["ts"]) * 1000,
            "y_actual": r["temperature"],
            "y_set": r["set_temperature"]
        })
    return jsonify(data)

@app.route('/cycles')
def list_cycles():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, start_time, end_time
        FROM cycles
        WHERE end_time IS NOT NULL
        ORDER BY end_time DESC
        LIMIT 10
    """)
    cycles = cur.fetchall()
    conn.close()
    return render_template('cycles.html', cycles=cycles)

@app.route('/cycles/<int:cycle_id>')
def show_cycle(cycle_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT start_time, end_time FROM cycles WHERE id = ?", (cycle_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        dt = row["end_time"] if row["end_time"] else row["start_time"]
        if isinstance(dt, str):
            try:
                dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
            except Exception as e:
                print("Error parsing date:", e)
                dt = datetime.now()
        cycle_date_str = dt.strftime("%B %d, %Y")
    else:
        cycle_date_str = "Unknown"
    return render_template('cycle_graph.html', cycle_id=cycle_id, cycle_date=cycle_date_str)

@app.route('/cycles/<int:cycle_id>/data')
def cycle_data(cycle_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT CAST((julianday(timestamp, 'localtime') - 2440587.5)*86400 AS INTEGER) AS ts,
               temperature,
               set_temperature
        FROM readings
        WHERE cycle_id = ?
        ORDER BY timestamp ASC
    """, (cycle_id,))
    rows = cur.fetchall()
    conn.close()
    print(f"Cycle {cycle_id} data: Found {len(rows)} readings")
    data = []
    for r in rows:
        data.append({
            "x": int(r["ts"]) * 1000,
            "y_actual": r["temperature"],
            "y_set": r["set_temperature"]
        })
    return jsonify(data)

@app.route('/status')
def status():
    return jsonify({
         "oven_on": config.get("oven_on", False),
         "timer_running": timer_running,
         "time_remaining": int(time_remaining)
    })

@app.route('/test_pwm', methods=['GET'])
def test_pwm():
    def pwm_test():
        if pwm is not None:
            print("Forcing PWM to 100% duty for 10 seconds")
            pwm.ChangeDutyCycle(100)
            time.sleep(10)
            pwm.ChangeDutyCycle(0)
            print("PWM test complete")
    threading.Thread(target=pwm_test, daemon=True).start()
    return "PWM test started"

@app.route('/test_readings')
def test_readings():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT cycle_id, timestamp, temperature, set_temperature
        FROM readings
        ORDER BY timestamp DESC
        LIMIT 10
    """)
    rows = cur.fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append({
            "cycle_id": r["cycle_id"],
            "timestamp": str(r["timestamp"]),
            "temperature": r["temperature"],
            "set_temperature": r["set_temperature"]
        })
    return jsonify(result)

if __name__ == '__main__':
    init_gpio()  # Initialize GPIO now
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
