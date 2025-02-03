import sys
import sx126x
import time
import select
import termios
import tty
import threading
from threading import Timer, Event

old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())

class SimplexLoRa:
    def __init__(self, node, receiver_addr):
        self.node = node
        self.receiver_addr = receiver_addr
        self.running = False
        self.thread = None
        self.last_temp_send = 0
        self.temp_interval = 2  # seconds
        self.mode_switch_event = Event()

    def run(self):
        print("Started listening mode (with periodic temperature updates)")
        print("Press Esc to exit")
        
        self.running = True
        while self.running:
            try:
                current_time = time.time()
                
                # Check if it's time to send temperature
                if current_time - self.last_temp_send >= self.temp_interval:
                    # Switch to transmit mode
                    self.send_temperature()
                    self.last_temp_send = current_time
                
                # Switch to receive mode
                try:
                    received_data = self.node.receive()
                    if received_data and received_data != "":
                        print(f"Received: {received_data}")
                except IndexError:
                    # Handle the common index error
                    pass
                except Exception as e:
                    print(f"Receive error: {e}")
                
                # Check for Esc key
                if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                    c = sys.stdin.read(1)
                    if c == '\x1b':
                        print("Exiting...")
                        self.running = False
                        break
                
                time.sleep(0.1)  # Small delay to prevent CPU overload

            except Exception as e:
                print(f"Operation error: {e}")
                time.sleep(0.1)

    def send_temperature(self):
        try:
            # Store current address
            current_addr = self.node.addr
            
            # Switch to transmit mode and send temperature
            self.node.set(self.node.freq, self.receiver_addr, self.node.power, self.node.rssi)
            temp = get_cpu_temp()
            self.node.send(f"CPU Temperature: {temp:.1f} C")
            
            # Switch back to receive mode
            time.sleep(0.2)
            self.node.set(self.node.freq, current_addr, self.node.power, self.node.rssi)
        except Exception as e:
            print(f"Error sending temperature: {e}")

    def start(self):
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)

def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as tempFile:
            cpu_temp = float(tempFile.read()) / 1000
        return cpu_temp
    except Exception as e:
        print(f"Error reading CPU temperature: {e}")
        return 0.0

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

def send_message(node):
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

    except ValueError:
        print("\nInvalid address format. Please use numbers for the address.")

try:
    node = setup_addresses()
    
    time.sleep(1)
    print("\nCommands:")
    print("Press Esc to exit")
    print("Press i   to send message")
    print("Press r   to start receive mode with temperature updates")

    while True:
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            c = sys.stdin.read(1)

            if c == '\x1b':  # Esc
                break
            elif c == '\x69':  # i
                send_message(node)
            elif c == '\x72':  # r
                receiver_addr = get_receiver_address()
                simplex_lora = SimplexLoRa(node, receiver_addr)
                simplex_lora.run()  # This will run until Esc is pressed

except Exception as e:
    print(f"Error occurred: {e}")

finally:
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)