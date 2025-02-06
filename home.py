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
node.set_mode(sx126x.MODE_RX)  # Start in RX mode

# --- Helper Functions ---
def get_cpu_temp():
    # ... (same as in motor.py - for completeness)
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

    if len(payload) < 5:
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
        print("Received Status: Motor {}, Total Run Time: {} seconds, Error Code: {}".