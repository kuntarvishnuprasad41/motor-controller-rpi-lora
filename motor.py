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
STATUS_UPDATE_INTERVAL = 300.0  # 5 minutes (300 seconds)
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
    try:
        tempFile = open("/sys/class/thermal/thermal_zone0/temp")
        cpu_temp = tempFile.read()
        tempFile.close()
        return float(cpu_temp) / 1000
    except:
        return -1.0

def load_value(filepath, default_value):
    try:
        with open(filepath, "r") as f:
            value_str = f.read()
            return int(value_str)
    except (FileNotFoundError, ValueError):
        return default_value

def save_value(filepath, value):
    try:
        with open(filepath, "w") as f:
            f.write(str(value))
    except Exception as e:
        print(f"Error saving to {filepath}: {e}")

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(RELAY_PIN_ON, GPIO.OUT)
    GPIO.setup(RELAY_PIN_OFF, GPIO.OUT)
    try:
        # GPIO.setup(POWER_LOSS_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        # # Re-enable power loss detection (after initial testing)
        # GPIO.add_event_detect(POWER_LOSS_PIN, GPIO.FALLING, callback=power_loss_callback, bouncetime=200)
        print("Power loss detection enabled.")
    except RuntimeError as e:
        print(f"Error setting up power loss detection: {e}")
        sys.exit(1)
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
    global motor_unit_state
    print(f"Power loss detected on channel {channel}!")
    if motor_unit_state != "TRANSMITTING_STATUS":
        node.cancel_receive()
        motor_unit_state = "TRANSMITTING_STATUS"
        send_power_loss_alert()

def send_power_loss_alert():
    global total_run_time, motor_on_time

    if motor_on_time > 0:
        current_time = int(time.time())
        total_run_time += current_time - motor_on_time
        save_value(TOTAL_RUNTIME_FILE, total_run_time)
        motor_on_time = 0
        save_value(MOTOR_ON_TIME_FILE, motor_on_time)

    message = construct_status_message(ERROR_CODE_POWER_FAILURE)
    print(f"send_power_loss_alert: Sending message: {message.hex()}")
    node.set_mode(node.MODE_TX)
    node.send(HOME_NODE_ADDRESS, message)  # Send to the home unit's address
    node.set_mode(node.MODE_RX)
    print(f"Sent power loss alert")

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
    print(f"construct_status_message: Constructed message: {bytes(message).hex()}")
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
    print("send_scheduled_update called")
    if motor_unit_state == "LISTENING":
        motor_unit_state = "TRANSMITTING_STATUS"
    # Re-schedule for 5 minutes later:
    scheduled_update_timer = Timer(STATUS_UPDATE_INTERVAL, send_scheduled_update)
    scheduled_update_timer.start()

# --- Main Program: Motor Unit ---
def main():
    global motor_unit_state, motor_running, motor_on_time, total_run_time, scheduled_update_timer, motor_run_timer

    setup_gpio()
    print("Motor Unit Initialized. Address:", NODE_ADDRESS)

    scheduled_update_timer = Timer(STATUS_UPDATE_INTERVAL, send_scheduled_update)
    scheduled_update_timer.start()
    node.set_mode(node.MODE_RX)

    try:
        while True:
            if motor_unit_state == "LISTENING":
                #print("State: LISTENING") # Removed extra print statements
                node.set_mode(node.MODE_RX)
                payload = node.receive()
                if payload:
                    print(f"Received payload: {payload.hex()}") # Keep this
                    message_type, data = parse_request(payload)
                    print(f"Parsed message_type: {message_type}, data: {data}")

                    if message_type == MSG_TYPE_ON:
                        motor_unit_state = "PROCESSING_REQUEST"
                        turn_on_motor()
                        motor_running = True
                        motor_on_time = int(time.time())
                        save_value(MOTOR_ON_TIME_FILE, motor_on_time)
                        motor_unit_state = "TRANSMITTING_RESPONSE"

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
                #print("State: TRANSMITTING_STATUS") # Removed extra print statements
                node.set_mode(node.MODE_TX)
                message = construct_status_message()
                node.send(HOME_NODE_ADDRESS, message)  # Send to the home unit's address
                node.set_mode(node.MODE_RX)  # Switch back to RX mode immediately
                motor_unit_state = "LISTENING"


            elif motor_unit_state == "TRANSMITTING_RESPONSE":
                #print("State: TRANSMITTING_RESPONSE") # Removed extra print statements
                node.set_mode(node.MODE_TX)
                message = construct_status_message()
                node.send(HOME_NODE_ADDRESS, message)  # Send to home unit's address
                node.set_mode(node.MODE_RX)
                motor_unit_state = "LISTENING"

            elif motor_unit_state == "PROCESSING_REQUEST":
                #print("State: PROCESSING_REQUEST") # Removed extra print statements
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
        print(f"An unexpected error occurred: {e}")
    finally:
        if scheduled_update_timer:
            scheduled_update_timer.cancel()
        node.set_mode(node.MODE_STDBY)
        GPIO.cleanup()

if __name__ == "__main__":
    main()