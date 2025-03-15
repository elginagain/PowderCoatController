# pid_autotune.py

import time
import math
from datetime import datetime
from temperature_sensor import read_temperature  # Use your sensor reading function


def auto_tune_pid(config, pwm, SSR_PIN):
    """
    Run a relay-based auto-tune experiment.

    Parameters:
      config: the global configuration dictionary (must contain "target_temperature")
      pwm: the PWM instance controlling the heater (SSR_PIN)
      SSR_PIN: the GPIO pin number for the heater control

    Returns a dictionary with tuned PID parameters: {"Kp": ..., "Ki": ..., "Kd": ...}

    This function assumes that the heater is controlled by switching the PWM fully ON (100%)
    and OFF (0%), and that the process variable (temperature) oscillates.
    """
    # Relay auto-tune parameters
    setpoint = config.get("target_temperature", 350)
    hysteresis = 2.0  # degrees F
    relay_amplitude = 50.0  # d (if output swings from 0 to 100, d = 50)
    test_duration = 120  # seconds for the auto-tune experiment

    # Lists to store switching times and temperatures
    switching_times = []
    measured_temps = []

    # Determine initial state based on current calibrated temperature
    current_temp = read_temperature()
    if current_temp < setpoint:
        current_state = 'on'
        pwm.ChangeDutyCycle(100)
    else:
        current_state = 'off'
        pwm.ChangeDutyCycle(0)

    start_time = time.time()
    print("Starting auto-tune relay experiment for {} seconds...".format(test_duration))

    # Run the relay experiment
    while time.time() - start_time < test_duration:
        current_temp = read_temperature()
        now = time.time()
        # If heater is ON and temp rises above setpoint + hysteresis, switch OFF
        if current_state == 'on' and current_temp > setpoint + hysteresis:
            pwm.ChangeDutyCycle(0)
            current_state = 'off'
            switching_times.append(now)
            measured_temps.append(current_temp)
            print("Switching OFF at temp {:.2f} at time {:.2f}".format(current_temp, now))
        # If heater is OFF and temp falls below setpoint - hysteresis, switch ON
        elif current_state == 'off' and current_temp < setpoint - hysteresis:
            pwm.ChangeDutyCycle(100)
            current_state = 'on'
            switching_times.append(now)
            measured_temps.append(current_temp)
            print("Switching ON at temp {:.2f} at time {:.2f}".format(current_temp, now))
        time.sleep(0.5)

    # End the relay test by turning off heater (PID will resume later)
    pwm.ChangeDutyCycle(0)
    print("Auto-tune experiment complete. Processing data...")

    # Need at least two switching events to compute period
    if len(switching_times) < 2:
        print("Not enough switching events for auto-tuning. Returning default parameters.")
        return {"Kp": 1.0, "Ki": 0.1, "Kd": 0.05}

    # Compute periods (assume every two switches represent one full cycle)
    periods = []
    for i in range(2, len(switching_times), 2):
        period = switching_times[i] - switching_times[i - 2]
        periods.append(period)
    if not periods:
        print("Unable to compute oscillation period. Returning default parameters.")
        return {"Kp": 1.0, "Ki": 0.1, "Kd": 0.05}
    Tu = sum(periods) / len(periods)
    print("Computed oscillation period (Tu): {:.2f} seconds".format(Tu))

    # Compute amplitude as half the difference between max and min measured temperatures
    max_temp = max(measured_temps)
    min_temp = min(measured_temps)
    A = (max_temp - min_temp) / 2.0
    print("Measured temperature amplitude (A): {:.2f}".format(A))

    if A == 0:
        print("Zero amplitude detected. Returning default PID parameters.")
        return {"Kp": 1.0, "Ki": 0.1, "Kd": 0.05}

    # Compute ultimate gain using relay method
    Ku = (4 * relay_amplitude) / (math.pi * A)
    print("Calculated ultimate gain (Ku): {:.2f}".format(Ku))

    # Ziegler-Nichols tuning formulas:
    Kp = 0.6 * Ku
    Ti = 0.5 * Tu  # Integral time
    Ki = Kp / Ti if Ti != 0 else 0.0
    Td = 0.125 * Tu  # Derivative time
    Kd = Kp * Td
    print("Tuned PID parameters: Kp = {:.2f}, Ki = {:.2f}, Kd = {:.2f}".format(Kp, Ki, Kd))

    return {"Kp": Kp, "Ki": Ki, "Kd": Kd}
