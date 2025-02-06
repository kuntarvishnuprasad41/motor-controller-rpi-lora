#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import sx126x
import time
import select
import termios
import tty
from threading import Timer

# --- Configuration (Home Unit Specific) ---
NODE_ADDRESS = 30      # Address of *this* node (Home Unit)
MOTOR_NODE_ADDRESS = 0  # Address of the Motor unit
FREQUENCY = 433         # LoRa frequency
POWER = 22             # Transmit power (dBm)
RSSI_ENABLED = False    # Whether to print RSSI
RESPONSE_TIMEOUT = 5.0      # Seconds

# --- Message Types (Constants) ---
MSG_TYPE_ON = 0x01
MSG_TYPE_OFF = 0x02
MSG_TYPE_STATUS_REQUEST = 0x03
MSG_TYPE_SET_TIMER = 0x04
MSG_TYPE_STATUS_UPDATE = 0x10
ERROR_CODE_NO_ERROR = 0x00
ERROR_CODE_POWER_FAILURE = 0x01

# --- State Machine Variables ---
home_unit_state = "LISTENING"
last_received_status = None
last_received_run_time = 0
request_timer = None

# --- LoRa Setup ---
# Note: The freq, addr, power, and rssi are set *here*.
node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=FREQUENCY, addr=NODE_ADDRESS, power=POWER, rssi=RSSI_ENABLED)


# --- Helper Functions ---
def get_cpu_temp():
    """Gets the Raspberry Pi CPU temperature."""
    try:
        tempFile = open("/sys/class/thermal/thermal_zone0/temp")
        cpu_temp = tempFile.read()
        tempFile.close()
        return float(cpu_temp) / 1000
    except:
        return -1.0  # Indicate an error reading temperature

def parse_and_display_status(payload):
    """Parses and displays a received status message."""
    global last_received_status, last_received_run_time

    if len(payload) < 5:  # Check for minimum length
        print("Received invalid status message (too short).")
        return

    message_type, motor_status, run_time_msb, run_time_lsb, error_code = payload[:5]

    if message_type != MSG_TYPE_STATUS_UPDATE:
        print("Received unexpected message type:", message_type)
        return

    last_received_run_time = (run_time_msb << 8) | run_time_lsb
    last_received_status = "ON" if motor_status == 0x01 else "OFF"
    if error_code == ERROR_CODE_POWER_FAILURE:
        print("Received Status: Motor OFF, Power Failure!  Total Run Time: {} seconds".format(last_received_run_time))

    elif error_code == ERROR_CODE_NO_ERROR:
         print("Received Status: Motor {}, Total Run Time: {} seconds".format(last_received_status, last_received_run_time))
    else:
        print("Received Status: Motor {}, Total Run Time: {} seconds, Error Code: {}".format(last_received_status, last_received_run_time,error_code))
def send_command(command_type, data=None):
    """Sends a command to the Motor unit."""
    global home_unit_state, request_timer

    message = [command_type]
    if data:
        message.extend(data) #Add data to the message
    node.set_mode(sx126x.MODE_TX) # Set the mode to TX
    node.send(bytes(message))
    #print(f"Sent command: {message}") # Debug
    node.set_mode(sx126x.MODE_RX) # Set back to RX mode
    home_unit_state = "WAITING_FOR_RESPONSE"

    # Start a timer to wait for the response
    request_timer = Timer(RESPONSE_TIMEOUT, handle_response_timeout)
    request_timer.start()

def handle_response_timeout():
    """Handles the timeout if no response is received."""
    global home_unit_state
    print("Error: No response from Motor unit.")
    home_unit_state = "LISTENING"

def set_timer():
    """Prompts the user to enter a timer duration and sends the command."""
    print("")  # Newline for cleaner output
    while True:
        duration_str = input("Enter timer duration in minutes (or 'c' to cancel): ")
        if duration_str.lower() == 'c':
            return  # Cancel the timer operation
        try:
            duration_minutes = int(duration_str)
            if duration_minutes > 0:
                send_command(MSG_TYPE_SET_TIMER, [duration_minutes])  # Send as a list
                return  # Exit the input loop
            else:
                print("Please enter a positive integer value.")
        except ValueError:
            print("Invalid input. Please enter a number or 'c'.")

# --- Main Program: Home Unit ---

# ... (rest of home.py) ...

def main():
    global home_unit_state, last_received_status, last_received_run_time, request_timer

    # Set up terminal for non-blocking input
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())

    print("Home Unit Initialized. Address:", NODE_ADDRESS)
    print("Commands: 1=ON, 2=OFF, 3=STATUS, 4=SET TIMER, Esc=Exit")

    try:
        while True:
            if home_unit_state == "LISTENING":
                # Check for user input (non-blocking)
                if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                    c = sys.stdin.read(1)
                    if c == '\x1b':  # Esc key
                        break
                    elif c == '1':
                        send_command(MSG_TYPE_ON)
                    elif c == '2':
                        send_command(MSG_TYPE_OFF)
                    elif c == '3':
                        send_command(MSG_TYPE_STATUS_REQUEST)
                    elif c == '4':
                        set_timer()

                # Listen for messages from the motor unit
                node.set_mode(node.MODE_RX) # Use node.MODE_RX
                payload = node.receive()
                if payload:
                    parse_and_display_status(payload)

            elif home_unit_state == "TRANSMITTING_REQUEST":
                #  send_command handles transmission
                pass

            elif home_unit_state == "WAITING_FOR_RESPONSE":
                node.set_mode(node.MODE_RX)  # Use node.MODE_RX
                payload = node.receive()
                if payload:
                    parse_and_display_status(payload)
                    if request_timer:
                        request_timer.cancel()
                    home_unit_state = "LISTENING"
                # Timeout handled by timer

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("Home Unit Shutting Down...")
    finally:
        if request_timer:
            request_timer.cancel()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        node.set_mode(node.MODE_STDBY) # Use node.MODE_STDBY

# ... (rest of home.py) ...
if __name__ == "__main__":
    main()