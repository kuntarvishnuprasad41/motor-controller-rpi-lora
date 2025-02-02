#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import sx126x
import time
import select
import termios
import tty
from threading import Timer

old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())

def get_cpu_temp():
    tempFile = open("/sys/class/thermal/thermal_zone0/temp")
    cpu_temp = tempFile.read()
    tempFile.close()
    return float(cpu_temp) / 1000


# Initialize Device 2 (Address 30)
node2 = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=30, power=22, rssi=False)

# Function to send CPU temperature to Device 1 (Address 1)
def send_cpu_to_device_1():
    node2.addr_temp = node2.addr
    node2.set(node2.freq, 1, node2.power, node2.rssi)
    node2.send("CPU Temperature: " + str(get_cpu_temp()) + " C")
    time.sleep(0.2)
    node2.set(node2.freq, node2.addr_temp, node2.power, node2.rssi)

# Function to receive data from Device 1 (Address 1)
def receive_data_from_device_1():
    node2.addr_temp = node2.addr
    node2.set(node2.freq, 1, node2.power, node2.rssi)
    received_data = node2.receive(timeout=2)  # wait for 2 seconds to receive data
    if received_data:
        print(f"Received from device 1: {received_data}")
    time.sleep(0.2)
    node2.set(node2.freq, node2.addr_temp, node2.power, node2.rssi)


# Function to handle key press and send/receive data accordingly
def handle_key_press(c):
    if c == '\x72':  # Press 'r' to send and receive data
        send_cpu_to_device_1()
        receive_data_from_device_1()


# Key press handling and program control
try:
    time.sleep(1)
    print("Press \033[1;32mEsc\033[0m to exit")
    print("Press \033[1;32mr\033[0m to send and receive CPU temperature to/from node 1")

    while True:
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            c = sys.stdin.read(1)

            # Detect key Esc
            if c == '\x1b':
                break
            # Detect key r
            elif c == '\x72':
                handle_key_press(c)

        sys.stdout.flush()

except Exception as e:
    print(f"Error: {e}")
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
