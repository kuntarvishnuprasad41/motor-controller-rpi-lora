import sys
import sx126x
import time
import select
import termios
import tty
import json
import RPi.GPIO as GPIO  # Import RPi.GPIO
import os 

# Initialize GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.OUT)  # Relay for ON
GPIO.setup(24, GPIO.OUT)  # Relay for OFF

GPIO.output(23, GPIO.LOW)
GPIO.output(24, GPIO.LOW)

DOUT_PIN = 25
GPIO.setup(DOUT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)






if os.isatty(sys.stdin.fileno()):  # Check if running in a terminal
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())
else:
    old_settings = None  # Prevent systemd from breaking

time.sleep(1)
# print("Enter curr node address (0-65535):")
# current_address = int(input())
current_address = 30


node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=current_address, power=22, rssi=False)
prev_state = "OFF"
on_from_remote = False

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
    reply_message = {"reply": message, "time": timestamp}  # Use "reply" key
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
    # print("Enter target node address (0-65535):")
    # target_address = int(input())
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
                        # time.sleep(0.5)
                        
                        # GPIO.output(23, GPIO.LOW)  # Turn ON relay 23
                        send_reply("Motor on", target_address)  # Send "Motor on" message
                        on_from_remote = True
                        prev_state = "ON"
                    elif command == "OFF":
                        GPIO.output(23, GPIO.LOW)   # Turn OFF relay 23
                        GPIO.output(24, GPIO.HIGH)  # Turn ON relay 24
                        time.sleep(0.5)
                        GPIO.output(24, GPIO.LOW)  # Turn ON relay 24
                        send_reply("Motor off", target_address) # Send "Motor off" message
                        on_from_remote = False
                        prev_state = "OFF"
                    elif command == "STATUS":
                        # Get status (ON/OFF) and send it.  This will be the most useful.
                        status = "ON" if GPIO.input(23) else "OFF"
                        send_reply(f"Motor is {status}", target_address)
                    else:
                        send_reply("Unknown command", target_address)

            except json.JSONDecodeError:
                print(f"Received non-JSON data: {received_data}")

        # value = GPIO.input(DOUT_PIN)  # Read digital output
        # print(f"Current Detected: {value}")
        # time.sleep(1)

        elif GPIO.input(DOUT_PIN):
            print("On Detected")
            if prev_state == "OFF":
                GPIO.output(24, GPIO.LOW)   # Turn OFF relay 24 (ensure only one is on)
                GPIO.output(23, GPIO.HIGH)
                send_command("ON", target_address)
                print(f"Inside: {GPIO.input(DOUT_PIN)}")

            time.sleep(1)
            prev_state = "ON"
        print(f"Prev State: {GPIO.input(DOUT_PIN)}")
        if not GPIO.input(DOUT_PIN):
            if prev_state == "ON":
                GPIO.output(23, GPIO.LOW)   # Turn OFF relay 23
                GPIO.output(24, GPIO.HIGH)  # Turn ON relay 24
                time.sleep(0.5)
                GPIO.output(24, GPIO.LOW)  # Turn ON relay 24
                send_reply("Motor off", target_address) # Send "Motor off" message
                # on_from_remote = False
                prev_state = "OFF"
                time.sleep(1)
                # prev_state = "ON"
            # send_command("OFF", target_address)
            # time.sleep(1)
        # elif not GPIO.input(DOUT_PIN):
        #     if(prev_state) == "ON" and not on_from_remote:
        #         GPIO.output(23, GPIO.LOW)   # Turn OFF relay 23
        #         GPIO.output(24, GPIO.HIGH)  # Turn ON relay 24
        #         time.sleep(0.5)
        #         GPIO.output(24, GPIO.LOW)  # Turn ON relay 24
        #         send_reply("Motor off", target_address) # Send "Motor off" message
        #         prev_state = "OFF"

        # if GPIO.input(DOUT_PIN) and not GPIO.input(23) and not GPIO.input(24):
        #     GPIO.output(24, GPIO.LOW)   # Turn OFF relay 24 (ensure only one is on)
        #     GPIO.output(23, GPIO.HIGH) 
        #     send_command("ON", target_address)



        


        time.sleep(0.01)

except ValueError:
    print("Invalid target address. Please enter a number between 0 and 65535.")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    if old_settings:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    GPIO.cleanup()