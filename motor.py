#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import sx126x
import time
import RPi.GPIO as GPIO
import os
from threading import Timer

# --- Configuration (Motor Unit Specific) ---
NODE_ADDRESS = 0       #  Address of *this* node (Motor Unit)
HOME_NODE_ADDRESS = 30   # Address of the Home Unit
FREQUENCY = 433         # LoRa frequency
POWER = 22             # Transmit power (dBm)
RSSI_ENABLED = False    # Whether to print RSSI
STATUS_UPDATE_INTERVAL = 10.0  # Seconds
RELAY_PIN_ON = 23 #  BCM pin connectoted to ON Relay
RELAY_PIN_OFF = 24 #  BCM pin connectoted to OFF Relay
POWER_LOSS_PIN = 25 #  BCM pin to check power loss

# --- Message Types (Constants) ---
MSG_TYPE_ON = 0x01
MSG_TYPE_OFF = 0x02
MSG_TYPE_STATUS_REQUEST = 0x03
MSG_TYPE_SET_TIMER = 0x04
MSG_TYPE_STATUS_UPDATE = 0x10
ERROR_CODE_NO_ERROR = 0x00
ERROR_CODE_POWER_FAILURE = 0x01

# --- File Paths (for persistent storage) ---
TOTAL_RUNTIME_FILE = "total_runtime_motor.txt"  # Unique file for motor unit
MOTOR_ON_TIME_FILE = "motor_on_time_motor.txt"    # Unique file for motor unit

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

def load_value(filepath, default_value):
    """Loads a value from a file, returning a default if file error"""
    try:
        with open(filepath, "r") as f:
            value_str = f.read()
            return int(value_str)  # Or float(value_str)
    except (FileNotFoundError, ValueError):
        return default_value

def save_value(filepath, value):
    """Saves a value to a file."""
    try:
        with open(filepath, "w") as f:
            f.write(str(value))
    except Exception as e:
        print(f"Error saving to {filepath}: {e}")

def setup_gpio():
    """Sets up GPIO pins for the motor unit."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)  # Suppress warnings (optional, but generally good)

    # Set up relay pins
    GPIO.setup(RELAY_PIN_ON, GPIO.OUT)
    GPIO.setup(RELAY_PIN_OFF, GPIO.OUT)

    # Set up power loss detection pin *with error handling*
    try:
        GPIO.setup(POWER_LOSS_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        # Temporarily disable for initial testing:
        #GPIO.add_event_detect(POWER_LOSS_PIN, GPIO.FALLING, callback=power_loss_callback, bouncetime=200)
        print("Power loss detection enabled.")
    except RuntimeError as e:
        print(f"Error setting up power loss detection: {e}")
        print("  - Make sure no other processes are using GPIO {POWER_LOSS_PIN}.")
        print("  - Ensure you are running the script with sudo (sudo python3 motor.py).")
        print("  - Check your wiring and voltage divider circuit.")
        sys.exit(1)  # Exit the program if GPIO setup fails
    except Exception as e:
        print(f"An unexpected error occurred during GPIO setup: {e}")
        sys.exit(1)

def turn_on_motor():
    GPIO.output(RELAY_PIN_ON, GPIO.HIGH)
    time.sleep(0.1)
    GPIO.output(RELAY_PIN_ON, GPIO.LOW)
    print("Motor ON")

def turn_off_motor():
    GPIO.output(RELAY_PIN_OFF, GPIO.HIGH)
    time.sleep(0.1)
    GPIO.output(RELAY_PIN_OFF, GPIO.LOW)
    print("Motor OFF")

def power_loss_callback(channel):
    """Handles power loss detection.  Runs in a separate thread!"""
    global motor_unit_state
    # print(f"Power loss detected on channel {channel}!")  # Debugging
    # The callback function MUST be fast.  Avoid doing lengthy operations here.
    if motor_unit_state != "TRANSMITTING_STATUS":
        node.cancel_receive()  # Immediately stop any ongoing receive
        motor_unit_state = "TRANSMITTING_STATUS"
        # We call send_power_loss_alert() directly.  It handles sending the message.
        send_power_loss_alert()

def send_power_loss_alert():
    """Sends a power loss alert message."""
    global total_run_time, motor_on_time

    if motor_on_time > 0:
        current_time = int(time.time())
        total_run_time += current_time - motor_on_time
        save_value(TOTAL_RUNTIME_FILE, total_run_time)
        motor_on_time = 0 # Reset
        save_value(MOTOR_ON_TIME_FILE, motor_on_time)

    message = construct_status_message(ERROR_CODE_POWER_FAILURE)
    node.set_mode(node.MODE_TX) # Set the mode to TX
    node.send(message)
    node.set_mode(node.MODE_RX) # Set back to RX
    print(f"Sent power loss alert")

# --- Message Parsing Functions ---
def parse_request(message):
    if len(message) < 1:
        return None, None
    message_type = message[0]
    data = None
    if len(message) > 1:
        data = message[1:]
    return message_type, data

def construct_status_message(error_code=ERROR_CODE_NO_ERROR):
    global motor_running, total_run_time, motor_on_time

    if motor_running:
        motor_status = 0x01
        current_time = int(time.time())
        total_run_time += current_time - motor_on_time
        save_value(TOTAL_RUNTIME_FILE, total_run_time)
        motor_on_time = current_time
        save_value(MOTOR_ON_TIME_FILE, motor_on_time)
    else:
        motor_status = 0x00

    message = [MSG_TYPE_STATUS_UPDATE, motor_status, (total_run_time >> 8) & 0xFF, total_run_time & 0xFF, error_code]
    return bytes(message)

# --- State Machine Variables ---
motor_unit_state = "LISTENING"
motor_running = False
motor_on_time = load_value(MOTOR_ON_TIME_FILE, 0)
total_run_time = load_value(TOTAL_RUNTIME_FILE, 0)
scheduled_update_timer = None
motor_run_timer = 0

# --- LoRa Setup ---
node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=FREQUENCY, addr=NODE_ADDRESS, power=POWER, rssi=RSSI_ENABLED)

def send_scheduled_update():
    global motor_unit_state, scheduled_update_timer
    if motor_unit_state == "LISTENING":
        motor_unit_state = "TRANSMITTING_STATUS"
    scheduled_update_timer = Timer(STATUS_UPDATE_INTERVAL, send_scheduled_update)
    scheduled_update_timer.start()

# --- Main Program: Motor Unit ---
def main():
    global motor_unit_state, motor_running, motor_on_time, total_run_time, scheduled_update_timer, motor_run_timer

    setup_gpio()  # Set up GPIO *before* any LoRa operations
    print("Motor Unit Initialized. Address:", NODE_ADDRESS)

    scheduled_update_timer = Timer(STATUS_UPDATE_INTERVAL, send_scheduled_update)
    scheduled_update_timer.start()
    node.set_mode(node.MODE_RX)

    try:
        while True:
            if motor_unit_state == "LISTENING":
                print("State: LISTENING") # Debug print
                node.set_mode(node.MODE_RX)
                payload = node.receive()
                if payload:
                    print(f"Received payload: {payload}")  # Debug print
                    message_type, data = parse_request(payload)
                    print(f"Received: {payload}") # Debug

                    if message_type == MSG_TYPE_ON:
                        motor_unit_state = "PROCESSING_REQUEST"
                        turn_on_motor()
                        motor_running = True
                        motor_on_time = int(time.time())
                        save_value(MOTOR_ON_TIME_FILE, motor_on_time)
                        motor_unit_state = "TRANSMITTING_RESPONSE"
                        print(f"Received: {payload} + motor_unit_state") # Debug


                    elif message_type == MSG_TYPE_OFF:
                        motor_unit_state = "PROCESSING_REQUEST"
                        turn_off_motor()
                        motor_running = False
                        if motor_on_time > 0:
                            current_time = int(time.time())
                            total_run_time += current_time - motor_on_time
                            save_value(TOTAL_RUNTIME_FILE, total_run_time)
                            motor_on_time = 0
                            save_value(MOTOR_ON_TIME_FILE, motor_on_time)
                        motor_run_timer = 0
                        motor_unit_state = "TRANSMITTING_RESPONSE"

                    elif message_type == MSG_TYPE_STATUS_REQUEST:
                        motor_unit_state = "TRANSMITTING_RESPONSE"

                    elif message_type == MSG_TYPE_SET_TIMER:
                        motor_unit_state = "PROCESSING_REQUEST"
                        try:
                            timer_minutes = int(data[0])
                            motor_run_timer = timer_minutes * 60
                            turn_on_motor()
                            motor_running = True
                            motor_on_time = int(time.time())
                            save_value(MOTOR_ON_TIME_FILE, motor_on_time)
                            motor_unit_state = "TRANSMITTING_RESPONSE"
                        except (ValueError, IndexError, TypeError):
                            print("Invalid timer value received.")
                            motor_unit_state = "LISTENING"

            elif motor_unit_state == "TRANSMITTING_STATUS":
                print("State: TRANSMITTING_STATUS") # Debug print
                node.set_mode(node.MODE_TX)
                message = construct_status_message()
                node.send(message)
                #print(f"Sent Status: {message}") # Debug
                motor_unit_state = "LISTENING"

            elif motor_unit_state == "TRANSMITTING_RESPONSE":
                print("State: TRANSMITTING_RESPONSE") # Debug print
                node.set_mode(node.MODE_TX)
                message = construct_status_message()
                node.send(message)
                #print(f"Sent Response: {message}") # Debug
                motor_unit_state = "LISTENING"

            elif motor_unit_state == "PROCESSING_REQUEST":
                print("State: PROCESSING_REQUEST") # Debug print
                pass

            if motor_running and motor_run_timer > 0:
                current_time = int(time.time())
                if current_time - motor_on_time >= motor_run_timer:
                    turn_off_motor()
                    motor_running = False
                    if motor_on_time > 0:
                        total_run_time += current_time - motor_on_time
                        save_value(TOTAL_RUNTIME_FILE, total_run_time)
                    motor_on_time = 0
                    save_value(MOTOR_ON_TIME_FILE, motor_on_time)
                    motor_run_timer = 0
                    motor_unit_state = "TRANSMITTING_STATUS"

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("Motor Unit Shutting Down...")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")  # Catch-all for other errors
    finally:
        if scheduled_update_timer:
            scheduled_update_timer.cancel()
        node.set_mode(node.MODE_STDBY)
        GPIO.cleanup()  # Always clean up GPIO pins!

if __name__ == "__main__":
    main()