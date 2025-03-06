# PCoven - Powder Coating Oven Controller

PCoven is a Raspberry Pi-powered web interface for controlling a powder coating oven.

## Features
- **Web-based UI** for temperature control, PID auto-tuning, and probe calibration.
- **Real-time graphs** for monitoring temperature performance.
- **Touchscreen-optimized interface** for ease of use on a 5" display.
- **Persistent settings storage** using JSON configuration.
- **Simple setup with automated dependency installation**.
- **Auto-starts on Raspberry Pi boot-up** and shows a loading screen.
- **Soft shutdown via hardware power switch** (turns off display, heater, and lights but keeps Raspberry Pi running).
- **Software shutdown option** from settings (safe power-off to prevent SD card corruption).

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/PCoven.git
cd PCoven
```

### 2. Run Setup Script
```bash
chmod +x setup.sh
./setup.sh
```

### 3. Enable Auto-Start on Boot
```bash
sudo cp pcoven.service /etc/systemd/system/
sudo systemctl enable pcoven
sudo systemctl start pcoven
```

### 4. Reboot the Raspberry Pi
```bash
sudo reboot
```

### 5. Access the Web Interface
After reboot, the interface will launch automatically. To access it from another device:
```
http://<your_raspberry_pi_ip>:5000
```

## GPIO Pin Assignments
- **Heating Element Control (SSR):** Raspberry Pi **GPIO 17**
- **Oven Light Control (Relay):** Raspberry Pi **GPIO 27**
- **Soft Shutdown Power Switch:** Raspberry Pi **GPIO 22**

These pins can be modified in `app.py` if needed.

## Directory Structure
```
PCoven/
│── app.py                 # Main Flask application
│── templates/
│   ├── dashboard.html      # Main Oven Control Page
│   ├── settings.html       # Settings Page
│   ├── pid_autotune.html   # PID Auto-Tune Page
│   ├── temperature_calibration.html  # Temperature Calibration Page
│── static/
│   ├── style.css           # CSS Styling (if needed)
│   ├── script.js           # JavaScript Functions (if needed)
│── config.json             # Stores persistent settings
│── requirements.txt        # Dependencies
│── setup.sh                # Auto-install script
│── pcoven.service          # Systemd service file for auto-start
│── README.md               # GitHub Documentation
│── .gitignore              # Ignore unnecessary files
```

## Contributing
Feel free to submit pull requests or raise issues!

## License
MIT License
