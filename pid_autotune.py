import time
import math
from temperature_sensor import read_temperature


def auto_tune_pid():
    """
    Performs a relay-feedback based auto-tuning algorithm over 10 minutes.

    The algorithm toggles the heater output (relay mode) for 10 minutes while recording
    temperature readings every second. The relay is ON for 60 seconds and OFF for 60 seconds.

    After the test period, the algorithm detects peaks and troughs to estimate the oscillation period (Pu)
    and amplitude (A). Then, using a relay half-swing (h=50, assuming a 0-100% output swing),
    it computes the ultimate gain Ku and uses Ziegler–Nichols rules:

        Kp = 0.6 * Ku
        Ki = 1.2 * Ku / Pu
        Kd = 0.075 * Ku * Pu

    Returns:
        dict: Tuned PID parameters (Kp, Ki, Kd)
    """
    tuning_duration = 600  # seconds (10 minutes)
    relay_on_time = 60  # seconds heater is ON
    relay_off_time = 60  # seconds heater is OFF
    sample_interval = 1  # seconds between samples

    readings = []  # List to store (time, temperature) readings
    start_time = time.time()
    current_time = start_time
    relay_state = True  # Start with heater ON
    next_toggle = current_time + relay_on_time

    print("Starting PID auto-tuning relay test for 10 minutes...")
    while current_time - start_time < tuning_duration:
        t = time.time() - start_time  # relative time in seconds
        temp = read_temperature()  # raw sensor reading
        readings.append((t, temp))

        if time.time() >= next_toggle:
            relay_state = not relay_state
            # In an actual system, you would toggle the heater output here.
            print(f"Relay toggled to {'ON' if relay_state else 'OFF'} at t={time.time() - start_time:.1f}s")
            next_toggle = time.time() + (relay_on_time if relay_state else relay_off_time)
        time.sleep(sample_interval)
        current_time = time.time()

    # Detect peaks and troughs in the readings
    peaks = []
    troughs = []
    for i in range(1, len(readings) - 1):
        prev_temp = readings[i - 1][1]
        curr_temp = readings[i][1]
        next_temp = readings[i + 1][1]
        if curr_temp > prev_temp and curr_temp > next_temp:
            peaks.append((readings[i][0], curr_temp))
        if curr_temp < prev_temp and curr_temp < next_temp:
            troughs.append((readings[i][0], curr_temp))

    if len(peaks) < 2 or len(troughs) < 2:
        print("Not enough oscillation detected for auto-tuning.")
        return {"Kp": 1.0, "Ki": 0.0, "Kd": 0.0}

    # Compute average period Pu from peak-to-peak differences
    peak_periods = [peaks[i][0] - peaks[i - 1][0] for i in range(1, len(peaks))]
    Pu = sum(peak_periods) / len(peak_periods)

    # Compute average amplitude A from peaks and troughs (pairwise)
    amplitudes = []
    for i in range(min(len(peaks), len(troughs))):
        amplitudes.append(peaks[i][1] - troughs[i][1])
    A = sum(amplitudes) / len(amplitudes)

    # h is half the output swing; assuming a 0-100% output, h = 50.
    h = 50.0
    Ku = (4 * h) / (math.pi * A)

    Kp = 0.6 * Ku
    Ki = 1.2 * Ku / Pu
    Kd = 0.075 * Ku * Pu

    print(f"Auto-tuning complete. Ku={Ku:.2f}, Pu={Pu:.2f}")
    print(f"Tuned parameters: Kp={Kp:.2f}, Ki={Ki:.2f}, Kd={Kd:.2f}")

    return {"Kp": Kp, "Ki": Ki, "Kd": Kd}
