import sys
import sx126x
import time
import select
import termios
import tty
import json
import RPi.GPIO as GPIO  # Import RPi.GPIO

# Initialize GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.OUT)  # Relay for ON
GPIO.setup(24, GPIO.OUT)  # Relay for OFF

old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())

time.sleep(1)
print("Enter curr node address (0-65535):")
current_address = int(input())

node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=current_address, power=22, rssi=False)

def send_command(command, target_address):
    # ... (No changes needed here)

def send_reply(message, target_address):
    # ... (No changes needed here)

try:
    time.sleep(1)
    print("Enter target node address (0-65535):")
    target_address = int(input())

    while True:
        received_data = node.receive()
        if received_data:
            try:
                received_json = json.loads(received_data)
                if "command" in received_json:
                    command = received_json["command"]
                    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                    print(f"[{current_time}] Received command: {command}")

                    if command == "ON":
                        GPIO.output(23, GPIO.HIGH)  # Turn ON relay 23
                        GPIO.output(24, GPIO.LOW)   # Turn OFF relay 24 (ensure only one is on)
                        send_reply("Motor on", target_address)  # Send "Motor on" message
                    elif command == "OFF":
                        GPIO.output(23, GPIO.LOW)   # Turn OFF relay 23
                        GPIO.output(24, GPIO.HIGH)  # Turn ON relay 24
                        send_reply("Motor off", target_address) # Send "Motor off" message
                    elif command == "STATUS":
                        # Get status (ON/OFF) and send it.  This will be the most useful.
                        status = "ON" if GPIO.input(23) else "OFF"
                        send_reply(f"Motor is {status}", target_address)
                    else:
                        send_reply("Unknown command", target_address)

            except json.JSONDecodeError:
                print(f"Received non-JSON data: {received_data}")

        time.sleep(0.01)

except ValueError:
    print("Invalid target address. Please enter a number between 0 and 65535.")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    GPIO.cleanup()  # Clean up GPIO on exit