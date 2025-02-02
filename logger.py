#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import sx126x
import threading
import time
import select
import termios
import tty
import logging
from threading import Timer

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())

def get_cpu_temp():
    try:
        tempFile = open("/sys/class/thermal/thermal_zone0/temp")
        cpu_temp = tempFile.read()
        tempFile.close()
        logger.debug(f"CPU temperature read: {cpu_temp}")
        return float(cpu_temp) / 1000
    except Exception as e:
        logger.error(f"Failed to read CPU temperature: {e}")
        return None

node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=30, power=22, rssi=False)
# node = sx126x.sx126x(serial_num="/dev/tty0", freq=433, addr=100, power=22, rssi=True)

def send_deal():
    get_rec = ""
    logger.debug("Awaiting input for sending data...")
    print("")
    print("input a string such as \033[1;32m20,Hello World\033[0m,it will send `Hello World` to node of address 20 ", flush=True)
    print("please input and press Enter key:", end='', flush=True)

    while True:
        rec = sys.stdin.read(1)
        if rec != None:
            if rec == '\x0a': break
            get_rec += rec
            sys.stdout.write(rec)
            sys.stdout.flush()
    
    logger.debug(f"Input received: {get_rec}")
    get_t = get_rec.split(",")
    
    try:
        node.addr_temp = node.addr
        node.set(node.freq, int(get_t[0]), node.power, node.rssi)
        node.send(get_t[1])
        logger.debug(f"Message sent: {get_t[1]} to address {get_t[0]}")
        time.sleep(0.2)
        node.set(node.freq, node.addr_temp, node.power, node.rssi)
    except Exception as e:
        logger.error(f"Error sending data: {e}")

    print('\x1b[2A', end='\r')
    print(" "*100)
    print(" "*100)
    print(" "*100)
    print('\x1b[3A', end='\r')

def send_cpu_continue(send_to_who, continue_or_not=True):
    if continue_or_not:
        global timer_task
        global seconds
        try:
            node.send_to = send_to_who
            node.addr_temp = node.addr
            node.set(node.freq, node.send_to, node.power, node.rssi)
            cpu_temp = get_cpu_temp()
            if cpu_temp is not None:
                node.send(f"CPU Temperature: {cpu_temp} C")
                logger.debug(f"Sent CPU Temperature: {cpu_temp} C to {send_to_who}")
            time.sleep(0.2)
            node.set(node.freq, node.addr_temp, node.power, node.rssi)
            timer_task = Timer(seconds, send_cpu_continue, (send_to_who,))
            timer_task.start()
        except Exception as e:
            logger.error(f"Error in sending CPU temperature: {e}")
    else:
        try:
            node.send_to = send_to_who
            node.addr_temp = node.addr
            node.set(node.freq, node.send_to, node.power, node.rssi)
            cpu_temp = get_cpu_temp()
            if cpu_temp is not None:
                node.send(f"CPU Temperature: {cpu_temp} C")
                logger.debug(f"Sent CPU Temperature: {cpu_temp} C to {send_to_who}")
            time.sleep(0.2)
            node.set(node.freq, node.addr_temp, node.power, node.rssi)
            timer_task.cancel()
        except Exception as e:
            logger.error(f"Error stopping CPU temperature sending: {e}")
    
try:
    time.sleep(1)
    logger.info("Press \033[1;32mEsc\033[0m to exit")
    logger.info("Press \033[1;32mi\033[0m to send a message")
    logger.info("Press \033[1;32ms\033[0m to send CPU temperature every 10 seconds")
    send_to_who = 0
    seconds = 2
    
    while True:
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            c = sys.stdin.read(1)

            # Detect key Esc
            if c == '\x1b':
                logger.info("Exiting the program.")
                break
            # Detect key i
            if c == '\x69':
                send_deal()
            # Detect key s
            if c == '\x73':
                logger.info("Starting to send CPU temperature at regular intervals.")
                print("Press \033[1;32mc\033[0m to exit the send task")
                timer_task = Timer(seconds, send_cpu_continue, (send_to_who,))
                timer_task.start()
                
                while True:
                    if sys.stdin.read(1) == '\x63':
                        logger.info("Stopping the CPU temperature send task.")
                        timer_task.cancel()
                        print('\x1b[1A', end='\r')
                        print(" "*100)
                        print('\x1b[1A', end='\r')
                        break

            sys.stdout.flush()

        node.receive()

except Exception as e:
    logger.error(f"An unexpected error occurred: {e}")
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
