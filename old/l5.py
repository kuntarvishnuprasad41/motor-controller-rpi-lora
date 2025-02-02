import RPi.GPIO as GPIO
import time
import sys
import termios
import tty

old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())

# Set up GPIO for Relay Control (GPIO 4)
RELAY_PIN = 6  # GPIO pin 4 connected to the relay module

# Set up GPIO mode
GPIO.setmode(GPIO.BCM)  # Use BCM pin numbering
GPIO.setup(RELAY_PIN, GPIO.OUT, initial=GPIO.HIGH)  # Set relay pin as output and default to HIGH (off for active-low relay)

# This function will turn the relay on or off
def control_relay(state):
    if state == "on":
        GPIO.output(RELAY_PIN, GPIO.LOW)  # Turn relay on (active-low)
        print("Relay is ON")
    elif state == "off":
        GPIO.output(RELAY_PIN, GPIO.HIGH)  # Turn relay off (active-low)
        print("Relay is OFF")

try:
    print("Press \033[1;32mEsc\033[0m to exit")
    print("Relay will continuously toggle on and off every second")

    relay_state = "off"  # Initial state of the relay

    while True:
        # Toggle relay state every second
        if relay_state == "off":
            control_relay("on")
            relay_state = "on"
        else:
            control_relay("off")
            relay_state = "off"
        
        time.sleep(1)  # Wait for 1 second before toggling again

except KeyboardInterrupt:
    pass
finally:
    GPIO.cleanup()  # Clean up GPIO settings
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
