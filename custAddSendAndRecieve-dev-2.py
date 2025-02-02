#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import sx126x
import time
import threading
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


# Initialize device with address 30
node2 = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=30, power=22, rssi=False)

# Function to receive data from device 1
def receive_data_from_device_1():
    node2.addr_temp = node2.addr
    node2.set(node2.freq, 1, node2.power, node2.rssi)
    start_time = time.time()
    
    while True:
        received_data = node2.receive()  # Receive without timeout argument
        if received_data:
            print(f"Received from device 1: {received_data}")
            break
        
        # Timeout after 2 seconds
        if time.time() - start_time > 2:
            print("Timeout: No data received from device 1")
            break

    time.sleep(0.2)
    node2.set(node2.freq, node2.addr_temp, node2.power, node2.rssi)

# Function to send CPU temperature
def send_cpu_temperature():
    node2.addr_temp = node2.addr
    node2.set(node2.freq, 1, node2.power, node2.rssi)
    node2.send("CPU Temperature:" + str(get_cpu_temp()) + " C")
    time.sleep(0.2)
    node2.set(node2.freq, node2.addr_temp, node2.power, node2.rssi)

# Function to handle keyboard inputs
def handle_keyboard_input():
    print("Press \033[1;32mEsc\033[0m to exit")
    print("Press \033[1;32mr\033[0m to send and receive CPU temperature to/from node 1")

    while True:
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            c = sys.stdin.read(1)

            # detect key Esc
            if c == '\x1b':
                break
            # detect key r to send/receive data
            elif c == '\x72':
                print("Press \033[1;32mc\033[0m to exit the send/receive task")
                timer_task = Timer(2, send_cpu_temperature)
                timer_task.start()

                while True:
                    receive_data_from_device_1()  # Receive from device 1
                    if sys.stdin.read(1) == '\x63':
                        timer_task.cancel()
                        print('\x1b[1A', end='\r')
                        print(" "*100)
                        print('\x1b[1A', end='\r')
                        break

    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

# Start the program
handle_keyboard_input()
