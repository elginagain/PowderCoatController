import RPi.GPIO as GPIO
import time

# Set up GPIO using BCM numbering.
GPIO.setmode(GPIO.BCM)
SSR_PIN = 17  # The pin connected to your SSR/LED
GPIO.setup(SSR_PIN, GPIO.OUT)

# Create a PWM instance with a frequency of 100Hz.
pwm = GPIO.PWM(SSR_PIN, 100)
pwm.start(0)  # Start with 0% duty cycle

print("PWM at 0% duty: LED should be off (or in its default state).")
time.sleep(5)

print("Setting PWM to 100% duty: LED should be fully on if active-high.")
pwm.ChangeDutyCycle(100)
time.sleep(5)

print("Setting PWM to 0% duty: LED should be off.")
pwm.ChangeDutyCycle(0)
time.sleep(5)

pwm.stop()
GPIO.cleanup()
print("Test complete.")
