#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import sx126x  # Your LoRa library
import time
import select
import termios
import tty
from threading import Timer

# --- Configuration (Home Unit Specific) ---
NODE_ADDRESS = 30       # Address of *this* node (Home Unit)
MOTOR_NODE_ADDRESS = 0   # Address of the Motor unit
FREQUENCY = 433          # LoRa frequency (MHz)
POWER = 22              # Transmit power (dBm)
RSSI_ENABLED = False     # Whether to print RSSI
RESPONSE_TIMEOUT = 5.0       # Seconds to wait for a response

# --- Message Types (Constants) ---
MSG_TYPE_ON = 0x01
MSG_TYPE_OFF = 0x02
MSG_TYPE_STATUS_REQUEST = 0x03
MSG_TYPE_SET_TIMER = 0x04
MSG_TYPE_STATUS_UPDATE = 0x10
ERROR_CODE_NO_ERROR = 0x00
ERROR_CODE_POWER_FAILURE = 0x01

# --- State Machine Variables ---
home_unit_state = "LISTENING"  # Current state of the home unit
last_received_status = None   # Last received motor status
last_received_run_time = 0    # Last received total run time
request_timer = None          # Timer object for response timeouts

# --- LoRa Setup ---
# Initialize the LoRa module.  Important: freq, addr, power, rssi.
node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=FREQUENCY, addr=NODE_ADDRESS, power=POWER, rssi=RSSI_ENABLED)

# --- Helper Functions ---

def get_cpu_temp():
    """Gets the Raspberry Pi CPU temperature (optional)."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as temp_file:
            cpu_temp = float(temp_file.read()) / 1000.0
        return cpu_temp
    except:
        return -1.0  # Return -1 if error


def parse_and_display_status(payload):
    """Parses and displays a received status message."""
    global last_received_status, last_received_run_time

    if len(payload) < 5:  # Check for minimum length (type, status, runtime MSB, runtime LSB, error)
        print("Received invalid status message (too short).")
        return

    message_type, motor_status, run_time_msb, run_time_lsb, error_code = payload[:5]

    if message_type != MSG_TYPE_STATUS_UPDATE:
        print("Received unexpected message type:", message_type)
        return

    last_received_run_time = (run_time_msb << 8) | run_time_lsb  # Combine MSB and LSB
    last_received_status = "ON" if motor_status == 0x01 else "OFF"

    if error_code == ERROR_CODE_POWER_FAILURE:
        print(f"Received Status: Motor OFF, Power Failure! Total Run Time: {last_received_run_time} seconds")
    elif error_code == ERROR_CODE_NO_ERROR:
        print(f"Received Status: Motor {last_received_status}, Total Run Time: {last_received_run_time} seconds")
    else:
        print(f"Received Status: Motor {last_received_status}, Total Run Time: {last_received_run_time} seconds, Error Code: {error_code}")



def send_command(command_type, data=None):
    """Sends a command to the Motor unit."""
    global home_unit_state, request_timer

    message = [command_type]
    if data:
        message.extend(data)  # Add any data to the message (e.g., timer duration)

    node.set_mode(node.MODE_TX)  # Switch to transmit mode
    node.send(bytes(message))      # Send the command
    node.set_mode(node.MODE_RX)  # Switch back to receive mode
    print(f"Sent command: {message}")  # Log the sent command

    home_unit_state = "WAITING_FOR_RESPONSE"  # Transition to waiting state

    # Start a timer to handle response timeouts
    request_timer = Timer(RESPONSE_TIMEOUT, handle_response_timeout)
    request_timer.start()


def handle_response_timeout():
    """Handles the timeout if no response is received."""
    global home_unit_state
    print("Error: No response from Motor unit.")
    home_unit_state = "LISTENING"  # Go back to listening state


def set_timer():
    """Prompts the user for a timer duration and sends the SET_TIMER command."""
    global home_unit_state  # Ensure we're modifying the global state

    print("")  # Add a newline for better readability
    while True:
        duration_str = input("Enter timer duration in minutes (or 'c' to cancel): ")
        if duration_str.lower() == 'c':
            return  # Cancel the timer setting
        try:
            duration_minutes = int(duration_str)
            if duration_minutes > 0:
                send_command(MSG_TYPE_SET_TIMER, [duration_minutes])  # Send duration as a list
                return  # Exit the loop after sending the command
            else:
                print("Please enter a positive integer value.")
        except ValueError:
            print("Invalid input. Please enter a number or 'c'.")



# --- Main Program: Home Unit ---

def main():
    global home_unit_state, last_received_status, last_received_run_time, request_timer

    # Set up the terminal for non-blocking input
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())

    print("Home Unit Initialized. Address:", NODE_ADDRESS)
    print("Commands: 1=ON, 2=OFF, 3=STATUS, 4=SET TIMER, Esc=Exit")

    try:
        while True:
            if home_unit_state == "LISTENING":
                # Check for user input (non-blocking)
                if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                    c = sys.stdin.read(1)  # Read a single character
                    if c == '\x1b':  # Escape key (exit)
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
                node.set_mode(node.MODE_RX)  # Ensure we are in RX mode
                payload = node.receive()    # Receive LoRa data
                if payload:
                    parse_and_display_status(payload) # Parse the received

            elif home_unit_state == "TRANSMITTING_REQUEST":
                #  The send_command function handles transmission
                pass  # We've already sent the command, so just wait

            elif home_unit_state == "WAITING_FOR_RESPONSE":
                node.set_mode(node.MODE_RX)  # Ensure in RX mode
                payload = node.receive()    # Wait for a response
                if payload:
                    parse_and_display_status(payload)  # Parse the response
                    if request_timer:
                        request_timer.cancel()       # Cancel the timeout timer
                    home_unit_state = "LISTENING"  # Go back to listening
                # else: Timeout is handled by handle_response_timeout()

            time.sleep(0.1)  # Short delay to avoid busy-waiting (100% CPU)

    except KeyboardInterrupt:
        print("Home Unit Shutting Down...")
    finally:
        if request_timer:
            request_timer.cancel()  # Cancel timer if it's running
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)  # Restore terminal settings
        node.set_mode(node.MODE_STDBY) # Put LoRa module to Sleep


if __name__ == "__main__":
    main()