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


# Initialize Device 1 (Address 1)
node1 = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=1, power=22, rssi=False)

# Send CPU temperature to Device 2 (Address 30)
def send_cpu_to_device_30():
    node1.addr_temp = node1.addr
    node1.set(node1.freq, 30, node1.power, node1.rssi)
    node1.send("CPU Temperature: " + str(get_cpu_temp()) + " C")
    time.sleep(0.2)
    node1.set(node1.freq, node1.addr_temp, node1.power, node1.rssi)

# Function to continuously receive data from other nodes
def receive_data():
    while True:
        data = node1.receive()  # Assuming node1.receive() will return the received data
        
        if data is not None:  # Check if data has been received
            print(f"Received from node 1: {data}")
            if data.startswith(b"CPU Temperature:"):
                print(f"Temperature Data: {data.decode()}")

        time.sleep(0.1)


# Key press handling and program control
try:
    time.sleep(1)
    print("Press \033[1;32mEsc\033[0m to exit")
    print("Press \033[1;32ms\033[0m to send CPU temperature to node 30")
    print("Press \033[1;32mr\033[0m to receive data")

    while True:
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            c = sys.stdin.read(1)

            # detect key Esc
            if c == '\x1b':
                break
            # detect key s
            elif c == '\x73':
                send_cpu_to_device_30()
            # detect key r to receive data
            elif c == '\x72':
                print("Receiving data...")
                receive_data()

        sys.stdout.flush()

except Exception as e:
    print(f"Error: {e}")
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
