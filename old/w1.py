#!/usr/bin/python
# -*- coding: UTF-8 -*-

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

def get_cpu_temp():
    tempFile = open("/sys/class/thermal/thermal_zone0/temp")
    cpu_temp = tempFile.read()
    tempFile.close()
    return float(cpu_temp) / 1000

node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=0, power=22, rssi=False)

def receive_continuous():
    print("Receiving data continuously. Press Esc to stop.")
    while True:
        node.receive()
        if node.rx_flag:
            print(f"Received: {node.rx_data}")
            node.rx_flag = False
        time.sleep(0.1)
        
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            c = sys.stdin.read(1)
            if c == '\x1b':  # Stop receiving on Esc
                print("Exiting receive mode")
                break

def send_deal():
    get_rec = ""
    print("\nInput a string such as \033[1;32m20,Hello World\033[0m")
    print("Please input and press Enter key:", end='', flush=True)

    while True:
        rec = sys.stdin.read(1)
        if rec == '\x0a':
            break
        get_rec += rec
        sys.stdout.write(rec)
        sys.stdout.flush()

    get_t = get_rec.split(",")
    node.addr_temp = node.addr
    node.set(node.freq, int(get_t[0]), node.power, node.rssi)
    node.send(get_t[1])
    time.sleep(0.2)
    node.set(node.freq, node.addr_temp, node.power, node.rssi)
    
    print("\x1b[2A", end='\r')
    print(" " * 100)
    print(" " * 100)
    print(" " * 100)
    print("\x1b[3A", end='\r')

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

try:
    time.sleep(1)
    print("Press \033[1;32mEsc\033[0m to exit")
    print("Press \033[1;32mi\033[0m   to send")
    print("Press \033[1;32ms\033[0m   to send CPU temperature every 10 seconds")
    print("Press \033[1;32mr\033[0m   to receive data continuously")

    send_to_who = 0
    seconds = 2

    while True:
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            c = sys.stdin.read(1)

            if c == '\x1b':  # Esc to exit
                break
            elif c == '\x69':  # 'i' to send data
                send_deal()
            elif c == '\x73':  # 's' to send CPU temp periodically
                print("Press \033[1;32mc\033[0m to exit the send task")
                timer_task = Timer(seconds, send_cpu_continue, (send_to_who,))
                timer_task.start()
                
                while True:
                    if sys.stdin.read(1) == '\x63':
                        timer_task.cancel()
                        print("\x1b[1A", end='\r')
                        print(" " * 100)
                        print("\x1b[1A", end='\r')
                        break
            elif c == '\x72':  # 'r' to receive data continuously
                receive_thread = threading.Thread(target=receive_continuous)
                receive_thread.start()

except:
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
