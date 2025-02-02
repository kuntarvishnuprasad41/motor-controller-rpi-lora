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


# Get CPU temperature of Raspberry Pi
def get_cpu_temp():
    tempFile = open("/sys/class/thermal/thermal_zone0/temp")
    cpu_temp = tempFile.read()
    tempFile.close()
    return float(cpu_temp) / 1000


# Initialize the LoRa node
node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=30, power=22, rssi=False)


# Function to send data
def send_deal():
    get_rec = ""
    print("")
    print("Input a string such as \033[1;32m20,Hello World\033[0m, it will send `Hello World` to node of address 20", flush=True)
    print("Please input and press Enter key:", end='', flush=True)

    while True:
        rec = sys.stdin.read(1)
        if rec != None:
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

    print('\x1b[2A', end='\r')
    print(" "*100)
    print(" "*100)
    print(" "*100)
    print('\x1b[3A', end='\r')


# Function to send CPU temperature every few seconds
def send_cpu_continue(send_to_who, continue_or_not=True):
    if continue_or_not:
        global timer_task
        global seconds
        node.send_to = send_to_who
        node.addr_temp = node.addr
        node.set(node.freq, node.send_to, node.power, node.rssi)
        node.send(f"Device: RaspberryPi, CPU Temperature: {get_cpu_temp()} C")
        time.sleep(0.2)
        node.set(node.freq, node.addr_temp, node.power, node.rssi)
        timer_task = Timer(seconds, send_cpu_continue, (send_to_who,))
        timer_task.start()
    else:
        node.send_to = send_to_who
        node.addr_temp = node.addr
        node.set(node.freq, node.send_to, node.power, node.rssi)
        node.send(f"Device: RaspberryPi, CPU Temperature: {get_cpu_temp()} C")
        time.sleep(0.2)
        node.set(node.freq, node.addr_temp, node.power, node.rssi)
        timer_task.cancel()


# Function to continuously receive data
# Function to continuously receive data
def receive_data():
    while True:
        try:
            # Attempt to receive data
            rx_data = node.receive()

            # Check if data is received and process it
            if rx_data:
                print(f"Received Data: {rx_data}")
            else:
                print("No data received. Waiting for incoming data...")
            
        except IndexError as e:
            print(f"Error: Received buffer is too small or empty, retrying... {e}")
        
        except Exception as e:
            print(f"Unexpected error during receiving: {e}")
        
        time.sleep(0.1)  # Small delay to prevent overloading the CPU


# Main loop
try:
    time.sleep(1)
    print("Press \033[1;32mEsc\033[0m to exit")
    print("Press \033[1;32mi\033[0m to send a message")
    print("Press \033[1;32ms\033[0m to send CPU temperature every 2 seconds")
    print("Press \033[1;32mr\033[0m to receive messages continuously")

    send_to_who = 0
    seconds = 2

    # Start the receive data thread
    receive_thread = threading.Thread(target=receive_data)
    receive_thread.daemon = True  # Daemonize to ensure it exits when the main thread exits
    receive_thread.start()

    while True:
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            c = sys.stdin.read(1)

            # Detect key Esc to exit
            if c == '\x1b':
                break

            # Detect key i to send data
            if c == '\x69':
                send_deal()

            # Detect key s to send CPU temperature
            if c == '\x73':
                print("Press \033[1;32mc\033[0m to exit the send task")
                timer_task = Timer(seconds, send_cpu_continue, (send_to_who,))
                timer_task.start()

                while True:
                    if sys.stdin.read(1) == '\x63':  # Detect key c to stop sending CPU temperature
                        timer_task.cancel()
                        print('\x1b[1A', end='\r')
                        print(" "*100)
                        print('\x1b[1A', end='\r')
                        break

            # Detect key r to start receiving continuously
            if c == '\x72':  # r for receive
                print("Receiving data continuously...")
                continue

            sys.stdout.flush()

        # Handle other tasks or message sending/receiving here

except:
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

# Reset terminal settings
termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
