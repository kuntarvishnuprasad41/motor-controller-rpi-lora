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
        address = input("Enter the device address (1-255): ")
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

# Send temperature data
def send_temperature_data(destination_address):
    while True:
        temp = get_cpu_temp()
        if temp is not None:
            node.addr_temp = node.addr
            node.set(node.freq, destination_address, node.power, node.rssi)
            node.send(f"CPU Temperature: {temp} C")
            time.sleep(2)  # Send every 2 seconds

# Receive data
def receive_data():
    while True:
        # Receive data and display the message
        received_data = node.receive()
        if received_data:
            print(f"Received data: {received_data}")
        time.sleep(0.1)

# Handle user input for sending/receiving
def handle_keyboard_input():
    print(f"Current device address: {current_device_address}")
    destination_address = input("Enter the destination device address (0-255): ")
    try:
        destination_address = int(destination_address)
        if destination_address < 0 or destination_address > 255:
            print("Invalid address, must be between 0 and 255.")
            return
    except ValueError:
        print("Invalid input. Please enter a valid address.")
        return

    # Start the continuous sending and receiving threads
    send_thread = threading.Thread(target=send_temperature_data, args=(destination_address,))
    receive_thread = threading.Thread(target=receive_data)

    send_thread.daemon = True
    receive_thread.daemon = True

    send_thread.start()
    receive_thread.start()

    # Wait for the threads to finish
    send_thread.join()
    receive_thread.join()

# Main loop to detect key presses
def main():
    print(f"Current device address: {current_device_address}")  # Display current address first
    print("Press Esc to exit")
    print("Press Enter to start sending/receiving data")

    while True:
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            c = sys.stdin.read(1)

            # Detect key Esc to exit
            if c == '\x1b':
                break
            # Detect Enter to start sending/receiving
            elif c == '\r':
                handle_keyboard_input()

    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram interrupted.")
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
