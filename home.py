import sys
import sx126x
import time
import select
import termios
import tty
import json
from threading import Timer

old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())

node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=30, power=22, rssi=False)

RECEIVE_DURATION = 2  # seconds

def send_command(command, target_address):
    """Sends a command and starts a timer for receiving."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    message = {"command": command, "time": timestamp}
    json_message = json.dumps(message)

    original_address = node.addr
    node.addr_temp = node.addr
    node.set(node.freq, target_address, node.power, node.rssi)
    node.send(json_message)
    node.set(node.freq, original_address, node.power, node.rssi)
    time.sleep(0.2)

    global receive_timer
    receive_timer = Timer(RECEIVE_DURATION, stop_receiving) #start timer
    receive_timer.start()
    global receiving_mode
    receiving_mode = True #set receiving mode to true
    print(f"Command sent to {target_address}. Entering receive mode for {RECEIVE_DURATION} seconds...")

def stop_receiving():
    global receiving_mode
    receiving_mode = False
    print("Receive mode ended.")


receiving_mode = False  # Flag to indicate if we're in receive mode
receive_timer = None

try:
    time.sleep(1)
    print("Enter target node address (0-65535):")
    target_address = int(input())

    print("Press \033[1;32m1\033[0m to send Motor ON command")
    print("Press \033[1;32m2\033[0m to send Motor OFF command")
    print("Press \033[1;32m3\033[0m to send Motor STATUS request")
    print("Press \033[1;32mEsc\033[0m to exit")

    while True:
        if not receiving_mode: #only check for input when not in receiving mode
            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                c = sys.stdin.read(1)

                if c == '\x1b':  # Esc key
                    break

                if c == '1':
                    send_command("ON", target_address)
                elif c == '2':
                    send_command("OFF", target_address)
                elif c == '3':
                    send_command("STATUS", target_address)

                sys.stdout.flush()

        if receiving_mode:
             # Call node.receive(). It prints the data itself.
            received_data = node.receive()  #get the received data
            time.sleep(0.1)  # Small delay
            if received_data:
                current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                print(f"[{current_time}] Received: {received_data}: ReceiveDataContinuously")
            time.sleep(0.1)

except ValueError:
    print("Invalid target address. Please enter a number between 0 and 65535.")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    if receive_timer:
        receive_timer.cancel()  # Cancel the timer if the program exits prematurely
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)