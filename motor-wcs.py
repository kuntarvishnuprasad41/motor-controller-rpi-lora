import sys
import sx126x
import time
import select
import termios
import tty
import json
import RPi.GPIO as GPIO
import os 

# Initialize GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.OUT)  # Relay for ON
GPIO.setup(24, GPIO.OUT)  # Relay for OFF
GPIO.setup(25, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  # WCS1700 Sensor Digital Output

GPIO.output(23, GPIO.LOW)
GPIO.output(24, GPIO.LOW)

if os.isatty(sys.stdin.fileno()):  
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())
else:
    old_settings = None  

time.sleep(1)

current_address = 30
node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=current_address, power=22, rssi=False)

def send_command(command, target_address):
    """Sends a command."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    message = {"command": command, "time": timestamp}
    json_message = json.dumps(message)

    original_address = node.addr
    node.addr_temp = node.addr
    node.set(node.freq, target_address, node.power, node.rssi)
    node.send(json_message)
    node.set(node.freq, original_address, node.power, node.rssi)
    time.sleep(0.2)
    print(f"Command sent to {target_address}.")

def send_reply(message, target_address):
    """Sends a reply."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    reply_message = {"reply": message, "time": timestamp}
    json_message = json.dumps(reply_message)

    original_address = node.addr
    node.addr_temp = node.addr
    node.set(node.freq, target_address, node.power, node.rssi)
    node.send(json_message)
    node.set(node.freq, original_address, node.power, node.rssi)
    time.sleep(0.2)
    print(f"Reply sent to {target_address}.")

try:
    time.sleep(1)
    target_address = 0

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
                        GPIO.output(24, GPIO.LOW)   # Turn OFF relay 24 (ensure only one is on)
                        GPIO.output(23, GPIO.HIGH)  # Turn ON relay 23
                        send_reply("Motor on", target_address)

                    elif command == "OFF":
                        GPIO.output(23, GPIO.LOW)   # Turn OFF relay 23
                        GPIO.output(24, GPIO.HIGH)  # Turn ON relay 24
                        time.sleep(0.5)
                        GPIO.output(24, GPIO.LOW)  # Ensure relay is OFF
                        send_reply("Motor off", target_address)

                    elif command == "STATUS":
                        # Get status from WCS1700 or relay
                        if GPIO.input(25):  # If current is detected
                            status = "ON (manual switch)"
                        elif GPIO.input(23):  # If relay is ON
                            status = "ON"
                        else:
                            status = "OFF"
                        send_reply(f"Motor is {status}", target_address)

                    else:
                        send_reply("Unknown command", target_address)

            except json.JSONDecodeError:
                print(f"Received non-JSON data: {received_data}")

        # **Check for Manual ON from WCS1700 and Turn ON Motor**
        if GPIO.input(25) and not GPIO.input(23):  # Detect current but motor is OFF
            print("[Manual Override] Motor turned ON manually.")
            GPIO.output(23, GPIO.HIGH)  # **Turn ON relay 23 (Motor ON)**
            send_reply("Motor is ON (manual switch)", target_address)
            time.sleep(5)  # Avoid multiple rapid detections

        time.sleep(0.01)

except ValueError:
    print("Invalid target address. Please enter a number between 0 and 65535.")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    if old_settings:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    GPIO.cleanup()
