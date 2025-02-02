#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import time
import threading
import select
import termios
import tty
import sx126x
from threading import Timer

# Device setup
def get_device_address():
    while True:
        address = input("Enter the current device address (1-255): ")
        try:
            address = int(address)
            if 1 <= address <= 255:
                return address
            else:
                print("Address must be between 1 and 255.")
        except ValueError:
            print("Invalid input. Please enter a valid address between 1 and 255.")

# Initialize the node with a user-defined address
current_device_address = get_device_address()
node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=current_device_address, power=22, rssi=False)

old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())

# Function to get CPU temperature
def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as temp_file:
            cpu_temp = temp_file.read()
        return float(cpu_temp) / 1000
    except:
        return None

# Function to get destination address
def get_destination_address():
    while True:
        dest_address = input("Enter the destination device address (1-255): ")
        try:
            dest_address = int(dest_address)
            if 1 <= dest_address <= 255:
                return dest_address
            else:
                print("Address must be between 1 and 255.")
        except ValueError:
            print("Invalid input. Please enter a valid address between 1 and 255.")

# Get destination address
destination_address = get_destination_address()

# Send temperature data to the destination address
def send_temperature_data():
    while True:
        temp = get_cpu_temp()
        if temp is not None:
            node.addr_temp = node.addr
            node.set(node.freq, destination_address, node.power, node.rssi)
            node.send("CPU Temperature: " + str(temp) + " C")
            time.sleep(2)  # Send every 2 seconds
            node.set(node.freq, node.addr_temp, node.power, node.rssi)

# Function to handle receiving data
def receive_data():
    while True:
        # Receive and print data
        node.receive()
        if node.rx_flag:
            print(f"Received from address {node.rx_addr}: {node.rx_data}")
            node.rx_flag = False  # Reset the flag after processing
        time.sleep(0.1)

# Keyboard input handler
def handle_keyboard_input():
    while True:
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            c = sys.stdin.read(1)

            # Detect key Esc to exit
            if c == '\x1b':
                break

            # Detect key r to start sending and receiving
            elif c == '\x72':  # 'r' key
                print(f"Sending and receiving data to/from address {destination_address}")
                threading.Thread(target=send_temperature_data, daemon=True).start()
                threading.Thread(target=receive_data, daemon=True).start()

        sys.stdout.flush()

try:
    print("Current device address:", current_device_address)
    print("Press \033[1;32mEsc\033[0m to exit")
    print("Press \033[1;32mr\033[0m to start sending and receiving data")

    handle_keyboard_input()

except Exception as e:
    print(f"Error: {e}")
finally:
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
