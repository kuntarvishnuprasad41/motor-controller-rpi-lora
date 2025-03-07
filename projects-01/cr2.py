import sys
import sx126x
import time
import select
import termios
import tty
import threading
from threading import Timer

old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())

def setup_addresses():
    print("\nSetup Device Addresses")
    print("---------------------")
    
    while True:
        try:
            print("Enter sender address (0-255): ", end='', flush=True)
            sender_input = ""
            while True:
                char = sys.stdin.read(1)
                if char == '\n':
                    break
                sender_input += char
                sys.stdout.write(char)
                sys.stdout.flush()
            
            sender_addr = int(sender_input)
            if 0 <= sender_addr <= 255:
                node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=sender_addr, power=22, rssi=False)
                print(f"\nDevice initialized with address: {sender_addr}")
                return node
            print("\nAddress must be between 0 and 255")
        except ValueError:
            print("\nPlease enter a valid number")

def get_receiver_address():
    while True:
        try:
            print("Enter receiver address (0-255): ", end='', flush=True)
            addr_input = ""
            while True:
                char = sys.stdin.read(1)
                if char == '\n':
                    break
                addr_input += char
                sys.stdout.write(char)
                sys.stdout.flush()
            
            addr = int(addr_input)
            if 0 <= addr <= 255:
                return addr
            print("\nAddress must be between 0 and 255")
        except ValueError:
            print("\nPlease enter a valid number")

def send_deal(node):
    get_rec = ""
    print("")
    print("Input format: <receiver_address>,<message>")
    print("Example: \033[1;32m20,Hello World\033[0m to send 'Hello World' to address 20")
    print("Please input and press Enter key:", end='', flush=True)

    while True:
        rec = sys.stdin.read(1)
        if rec != None:
            if rec == '\x0a': break
            get_rec += rec
            sys.stdout.write(rec)
            sys.stdout.flush()

    try:
        get_t = get_rec.split(",")
        if len(get_t) != 2:
            print("\nInvalid format. Use: receiver_address,message")
            return

        receiver_addr = int(get_t[0])
        if not (0 <= receiver_addr <= 255):
            print("\nReceiver address must be between 0 and 255")
            return

        node.addr_temp = node.addr
        node.set(node.freq, receiver_addr, node.power, node.rssi)
        node.send(get_t[1])
        time.sleep(0.2)
        node.set(node.freq, node.addr_temp, node.power, node.rssi)

        print('\x1b[2A', end='\r')
        print(" "*100)
        print(" "*100)
        print(" "*100)
        print('\x1b[3A', end='\r')
    except ValueError:
        print("\nInvalid address format. Please use numbers for the address.")

class TemperatureSender:
    def __init__(self, node, receiver_addr, interval=2):
        self.node = node
        self.receiver_addr = receiver_addr
        self.interval = interval
        self.running = False
        self.thread = None

    def send_temperature(self):
        while self.running:
            try:
                self.node.addr_temp = self.node.addr
                self.node.set(self.node.freq, self.receiver_addr, self.node.power, self.node.rssi)
                self.node.send(f"CPU Temperature: {get_cpu_temp()} C")
                time.sleep(0.2)
                self.node.set(self.node.freq, self.node.addr_temp, self.node.power, self.node.rssi)
                time.sleep(self.interval)
            except Exception as e:
                print(f"Error in temperature sender: {e}")
                self.running = False
                break

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self.send_temperature)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

def get_cpu_temp():
    tempFile = open("/sys/class/thermal/thermal_zone0/temp")
    cpu_temp = tempFile.read()
    tempFile.close()
    return float(cpu_temp) / 1000

def receive_data_continuously(node, temp_sender):
    print("Receiving data...")
    print("Press Esc to exit receive mode")
    
    while True:
        try:
            received_data = node.receive()
            
            if received_data:
                print(f"Received: {received_data}")
            
            time.sleep(0.1)

            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                c = sys.stdin.read(1)
                if c == '\x1b':
                    print("Exiting receive mode.")
                    temp_sender.stop()
                    break
        except Exception as e:
            print(f"Error in receive mode: {e}")
            temp_sender.stop()
            break

try:
    node = setup_addresses()
    
    time.sleep(1)
    print("\nCommands:")
    print("Press Esc to exit")
    print("Press i   to send message")
    print("Press s   to send cpu temperature every 2 seconds")
    print("Press r   to receive data (and send temperature updates)")

    while True:
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            c = sys.stdin.read(1)

            if c == '\x1b':  # Esc
                break
            elif c == '\x69':  # i
                send_deal(node)
            elif c == '\x73':  # s
                receiver_addr = get_receiver_address()
                temp_sender = TemperatureSender(node, receiver_addr)
                print("Press c to exit the send task")
                temp_sender.start()
                
                while True:
                    if sys.stdin.read(1) == '\x63':  # c
                        temp_sender.stop()
                        print('\x1b[1A', end='\r')
                        print(" "*100)
                        print('\x1b[1A', end='\r')
                        break
            
            elif c == '\x72':  # r
                receiver_addr = get_receiver_address()
                # Create and start temperature sender
                temp_sender = TemperatureSender(node, receiver_addr)
                temp_sender.start()
                # Start receiving (this will run until Esc is pressed)
                receive_data_continuously(node, temp_sender)

except Exception as e:
    print(f"Error occurred: {e}")

finally:
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)