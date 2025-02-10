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
GPIO.setup(23, GPIO.OUT)  # Relay for Motor ON
GPIO.setup(24, GPIO.OUT)  # Relay for Motor OFF
GPIO.setup(25, GPIO.IN)   # WCS1700 DOUT (Current Sensor Input)

# Ensure relays start in OFF position
GPIO.output(23, GPIO.LOW)
GPIO.output(24, GPIO.LOW)

if os.isatty(sys.stdin.fileno()):  # Check if running in a terminal
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())
else:
    old_settings = None  # Prevent systemd from breaking

time.sleep(1)

current_address = 30
node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=current_address, power=22, rssi=False)

def send_command(command, target_address):
    """Sends a command via LoRa."""
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
    """Sends a reply via LoRa."""
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
    target_address = 0  # Default target address

    prev_motor_state = None  # Track previous motor state

    while True:
        # ✅ Read current sensor (WCS1700 DOUT)
        current_detected = GPIO.input(25)  # 1 = Current flowing, 0 = No current

        if current_detected == 1 and prev_motor_state != "ON":
            # Turn on motor only if it was previously OFF
            GPIO.output(24, GPIO.LOW)   # Ensure OFF relay is LOW
            GPIO.output(23, GPIO.HIGH)  # Turn ON relay for motor
            send_reply("Motor turned ON due to current detection", target_address)
            prev_motor_state = "ON"  # Update state
        
        elif current_detected == 0 and prev_motor_state != "OFF":
            # Turn off motor only if it was previously ON
            GPIO.output(23, GPIO.LOW)   # Turn OFF relay for motor
            GPIO.output(24, GPIO.HIGH)  # Turn ON relay for OFF condition
            time.sleep(0.5)
            GPIO.output(24, GPIO.LOW)   # Turn OFF relay for OFF condition
            send_reply("Motor turned OFF due to no current", target_address)
            prev_motor_state = "OFF"  # Update state

        # ✅ Check for incoming LoRa messages
        received_data = node.receive()
        if received_data:
            try:
                received_json = json.loads(received_data)
                if "command" in received_json:
                    command = received_json["command"]
                    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                    print(f"[{current_time}] Received command: {command}")

                    if command == "ON" and prev_motor_state != "ON":
                        GPIO.output(24, GPIO.LOW)   # Ensure OFF relay is LOW
                        GPIO.output(23, GPIO.HIGH)  # Turn ON relay for motor
                        send_reply("Motor on", target_address)
                        prev_motor_state = "ON"
                    elif command == "OFF" and prev_motor_state != "OFF":
                        GPIO.output(23, GPIO.LOW)   # Turn OFF relay for motor
                        GPIO.output(24, GPIO.HIGH)  # Turn ON relay for OFF condition
                        time.sleep(0.5)
                        GPIO.output(24, GPIO.LOW)   # Turn OFF relay for OFF condition
                        send_reply("Motor off", target_address)
                        prev_motor_state = "OFF"
                    elif command == "STATUS":
                        status = "ON" if GPIO.input(23) else "OFF"
                        send_reply(f"Motor is {status}", target_address)
                    else:
                        send_reply("Unknown command", target_address)

            except json.JSONDecodeError:
                print(f"Received non-JSON data: {received_data}")

        time.sleep(0.5)  # Reduced loop speed for efficiency

except ValueError:
    print("Invalid target address. Please enter a number between 0 and 65535.")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    if old_settings:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    GPIO.cleanup()
