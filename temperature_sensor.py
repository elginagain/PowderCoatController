#!/usr/bin/env python3
import sys
import time

# Calibration offset in °F (adjust as needed)
CALIBRATION_OFFSET = 0.0

if sys.platform.startswith("linux"):
    import spidev  # Raspberry Pi SPI library

    # SPI Configuration for MAX31855
    SPI_BUS = 0
    SPI_DEVICE = 0


    def read_max31855():
        """
        Reads temperature from the MAX31855 sensor using spidev.

        Returns:
            float: Temperature in °F.
        """
        spi = spidev.SpiDev()
        spi.open(SPI_BUS, SPI_DEVICE)
        spi.max_speed_hz = 5000000  # Set SPI clock speed

        # Read 4 bytes from the sensor
        raw = spi.readbytes(4)
        spi.close()

        # Combine the 4 bytes into a single 32-bit integer
        raw_data = (raw[0] << 24) | (raw[1] << 16) | (raw[2] << 8) | raw[3]
        # The temperature data is in the top 14 bits (after shifting right by 18)
        temp_raw = raw_data >> 18
        # Check for negative temperature (if sign bit is set)
        if temp_raw & 0x2000:
            temp_raw -= 16384

        # Convert raw data to Celsius (each bit is 0.25°C)
        temp_c = temp_raw * 0.25
        # Convert Celsius to Fahrenheit
        temp_f = temp_c * 9.0 / 5.0 + 32.0
        return temp_f


    def read_temperature():
        """
        Returns the calibrated temperature reading in °F.
        """
        try:
            temp_f = read_max31855()
            return temp_f + CALIBRATION_OFFSET
        except Exception as e:
            print("Error reading temperature:", e)
            return None

else:
    # For non-Linux systems (e.g., Windows development), use a mock sensor.
    class MockMAX31855:
        def read_temp_f(self):
            return 77.0  # Dummy temperature for testing


    mock_sensor = MockMAX31855()


    def read_temperature():
        """
        Returns a mocked temperature reading in °F.
        """
        return mock_sensor.read_temp_f() + CALIBRATION_OFFSET

if __name__ == '__main__':
    print("Starting temperature sensor read loop. Press Ctrl+C to exit.")
    try:
        while True:
            temperature = read_temperature()
            if temperature is not None:
                print("Current Temperature: {:.2f} °F".format(temperature))
            else:
                print("Temperature reading failed.")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting temperature sensor read loop.")
