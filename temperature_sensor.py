import time
import Adafruit_GPIO.SPI as SPI
import Adafruit_MAX31855.MAX31855 as MAX31855

# Define your GPIO pins (adjust according to your wiring)
CLK_PIN = 11  # SCLK (clock pin)
CS_PIN = 8  # CS (chip select)
DO_PIN = 9  # MISO (data in)

# Initialize the MAX31855 sensor
sensor = MAX31855.MAX31855(CLK_PIN, CS_PIN, DO_PIN)

# Optional calibration offset (in Celsius)
CALIBRATION_OFFSET = 0.0


def read_temperature():
    """
    Reads the temperature from the MAX31855 sensor and applies calibration.

    Returns:
        float: Temperature in Celsius, or None if an error occurs.
    """
    try:
        # Read raw temperature in Celsius
        temp_c = sensor.readTempC()
        # Apply any calibration offset
        return temp_c + CALIBRATION_OFFSET
    except Exception as e:
        print("Error reading temperature:", e)
        return None


if __name__ == "__main__":
    # Test loop to print temperature every second
    while True:
        temperature = read_temperature()
        if temperature is not None:
            print("Current Temperature: {:.2f} °C".format(temperature))
        else:
            print("Failed to read temperature")
        time.sleep(1)
