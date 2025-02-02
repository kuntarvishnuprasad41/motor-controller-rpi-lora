#!/usr/bin/python
# -*- coding: UTF-8 -*-

#
#    this is an UART-LoRa device and there's firmware on Module
#    users can transfer or receive data directly via UART without setting parameters like coderate, spread factor, etc.
#    |============================================ |
#    |   It does not support LoRaWAN protocol !!!  |
#    | ============================================|
#   
#    This script is mainly for Raspberry Pi 3B+, 4B, and Zero series
#    Since PC/Laptop does not have GPIO to control HAT, it should be configured by
#    GUI and while setting the jumpers, 
#    Please refer to another script pc_main.py
#

import sys
import sx126x
import threading
import time
import select
import termios
import tty
from threading import Timer

old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())


#    The following is to obtain the temperature of the RPi CPU 
def get_cpu_temp():
    tempFile = open("/sys/class/thermal/thermal_zone0/temp")
    cpu_temp = tempFile.read()
    tempFile.close()
    return float(cpu_temp) / 1000

#   serial_num
#       PiZero, Pi3B+, and Pi4B use "/dev/ttyS0"
#
#    Frequency is [850 to 930], or [410 to 493] MHz
#
#    address is 0 to 65535
#
#    The tramsmit power is {10, 13, 17, and 22} dBm
#
#    RSSI (receive signal strength indicator) is {True or False}
#

# Set up the node
node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=100, power=22, rssi=True)

def send_deal():
    get_rec = ""
    print("")
    print("input a string such as \033[1;32m20,Hello World\033[0m, it will send `Hello World` to node of address 20", flush=True)
    print("please input and press Enter key:", end='', flush=True)

    while True:
        rec = sys.stdin.read(1)
        if rec != None:
            if rec == '\x0a': break
            get_rec += rec
            sys.stdout.write(rec)
            sys.stdout.flush()

    get_t = get_rec.split(",")
    
    node.addr_temp = node.addr
    node.set(node.freq, int(get_t[0]), node.power, node.rssi)
    node.send(get_t[1])
    time.sleep(0.2)
    node.set(node.freq, node.addr_temp, node.power, node.rssi)

    print('\x1b[2A', end='\r')
    print(" " * 100)
    print(" " * 100)
    print(" " * 100)
    print('\x1b[3A', end='\r')


def send_cpu_continue(send_to_who, continue_or_not=True):
    if continue_or_not:
        global timer_task
        global seconds
        node.send_to = send_to_who
        node.addr_temp = node.addr
        node.set(node.freq, node.send_to, node.power, node.rssi)
        node.send("CPU Temperature:" + str(get_cpu_temp()) + " C")
        time.sleep(0.2)
        node.set(node.freq, node.addr_temp, node.power, node.rssi)
        timer_task = Timer(seconds, send_cpu_continue, (send_to_who,))
        timer_task.start()
    else:
        node.send_to = send_to_who
        node.addr_temp = node.addr
        node.set(node.freq, node.send_to, node.power, node.rssi)
        node.send("CPU Temperature:" + str(get_cpu_temp()) + " C")
        time.sleep(0.2)
        node.set(node.freq, node.addr_temp, node.power, node.rssi)
        timer_task.cancel()
        pass

def handle_rssi():
    try:
        rssi_value = node.get_rssi()  # Hypothetical method for getting RSSI
        if rssi_value is not None:
            print(f"RSSI: {rssi_value} dBm")
        else:
            print("Error: Unable to read RSSI value")
    except Exception as e:
        print(f"Error while receiving RSSI: {e}")

try:
    time.sleep(1)
    print("Press \033[1;32mEsc\033[0m to exit")
    print("Press \033[1;32mi\033[0m to send")
    print("Press \033[1;32ms\033[0m to send CPU temperature every 10 seconds")
    send_to_who = 21
    seconds = 2

    while True:

        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            c = sys.stdin.read(1)

            # Detect key Esc
            if c == '\x1b':
                break
            # Detect key i
            if c == '\x69':
                send_deal()
            # Detect key s
            if c == '\x73':
                print("Press \033[1;32mc\033[0m to exit the send task")
                timer_task = Timer(seconds, send_cpu_continue, (send_to_who,))
                timer_task.start()

                while True:
                    if sys.stdin.read(1) == '\x63':
                        timer_task.cancel()
                        print('\x1b[1A', end='\r')
                        print(" " * 100)
                        print('\x1b[1A', end='\r')
                        break

            sys.stdout.flush()

        node.receive()
        handle_rssi()  # Handle and print RSSI after each receive
        time.sleep(0.1)

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
