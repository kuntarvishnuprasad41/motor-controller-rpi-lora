import RPi.GPIO as GPIO
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

# Setup GPIO for Relay Control
RELAY_PIN = 17  # GPIO pin connected to the relay module

# Set up GPIO mode
GPIO.setmode(GPIO.BCM)  # Use BCM pin numbering
GPIO.setup(RELAY_PIN, GPIO.OUT)  # Set the relay pin as an output

# This function will turn the relay on or off
def control_relay(state):
    if state == "on":
        GPIO.output(RELAY_PIN, GPIO.HIGH)  # Turn relay on
        print("Relay is ON")
    elif state == "off":
        GPIO.output(RELAY_PIN, GPIO.LOW)  # Turn relay off
        print("Relay is OFF")

# Function to get CPU temperature (as you already have)
def get_cpu_temp():
    tempFile = open( "/sys/class/thermal/thermal_zone0/temp" )
    cpu_temp = tempFile.read()
    tempFile.close()
    return float(cpu_temp)/1000

# Initialize LoRa (as in the existing code)
node = sx126x.sx126x(serial_num = "/dev/ttyAMA0",freq=433,addr=100,power=22,rssi=True)

# Send data over LoRa
def send_deal():
    get_rec = ""
    print("")
    print("input a string such as \033[1;32m20,Hello World\033[0m,it will send `Hello World` to node of address 20 ",flush=True)
    print("please input and press Enter key:",end='',flush=True)

    while True:
        rec = sys.stdin.read(1)
        if rec != None:
            if rec == '\x0a': break
            get_rec += rec
            sys.stdout.write(rec)
            sys.stdout.flush()

    get_t = get_rec.split(",")
    
    node.addr_temp = node.addr
    node.set(node.freq,int(get_t[0]),node.power,node.rssi)
    node.send(get_t[1])
    time.sleep(0.2)
    node.set(node.freq,node.addr_temp,node.power,node.rssi)

    print('\x1b[2A',end='\r')
    print(" "*100)
    print(" "*100)
    print(" "*100)
    print('\x1b[3A',end='\r')

# Main control loop
try:
    time.sleep(1)
    print("Press \033[1;32mEsc\033[0m to exit")
    print("Press \033[1;32mi\033[0m   to send")
    print("Press \033[1;32ms\033[0m   to send cpu temperature every 10 seconds")
    print("Press \033[1;32mr\033[0m   to control relay (on/off)")

    send_to_who = 21
    seconds = 2

    while True:

        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            c = sys.stdin.read(1)

            # Exit if Escape key is pressed
            if c == '\x1b':
                break

            # Send message if 'i' is pressed
            if c == '\x69':
                send_deal()

            # Send CPU temperature every 10 seconds if 's' is pressed
            if c == '\x73':
                print("Press \033[1;32mc\033[0m to exit the send task")
                timer_task = Timer(seconds,send_cpu_continue,(send_to_who,))
                timer_task.start()
                
                while True:
                    if sys.stdin.read(1) == '\x63':
                        timer_task.cancel()
                        print('\x1b[1A',end='\r')
                        print(" "*100)
                        print('\x1b[1A',end='\r')
                        break

            # Control relay if 'r' is pressed
            if c == '\x72':
                relay_command = input("Enter relay command (on/off): ")
                if relay_command == "on":
                    control_relay("on")
                elif relay_command == "off":
                    control_relay("off")
                else:
                    print("Invalid command. Use 'on' or 'off'.")

            sys.stdout.flush()

        # Receive data
        node.receive()

except:
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

# Clean up GPIO pins
GPIO.cleanup()
termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
