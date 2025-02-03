import RPi.GPIO as GPIO
import time
import select
import termios
import tty
import sys

old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())

# Set up GPIO for Relay Control (changed to GPIO 4)
RELAY_PIN = 4  # GPIO pin 4 connected to the relay module (for testing LED or relay)

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
    print("Press \033[1;32mr\033[0m to toggle relay on/off")

    relay_state = "off"  # Initial state of the relay

    while True:
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            c = sys.stdin.read(1)

            # Exit if Escape key is pressed
            if c == '\x1b':
                break

            # Toggle relay state if 'r' is pressed
            if c == '\x72':  # 'r' key
                if relay_state == "off":
                    control_relay("on")
                    relay_state = "on"
                else:
                    control_relay("off")
                    relay_state = "off"

except KeyboardInterrupt:
    pass
finally:
    GPIO.cleanup()  # Clean up GPIO settings
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
