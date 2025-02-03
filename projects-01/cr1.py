import sys
import sx126x
import time
import select
import termios
import tty
from threading import Timer

old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())

def setup_addresses():
    print("\nSetup Device Addresses")
    print("---------------------")
    
    # Get sender address
    while True:
        try:
            sender_addr = input("Enter sender address (0-255): ")
            sender_addr = int(sender_addr)
            if 0 <= sender_addr <= 255:
                break
            print("Address must be between 0 and 255")
        except ValueError:
            print("Please enter a valid number")
    
    # Initialize node with sender address
    node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=sender_addr, power=22, rssi=False)
    print(f"Device initialized with address: {sender_addr}")
    return node

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

def send_cpu_continue(node, send_to_who, continue_or_not=True):
    if continue_or_not:
        global timer_task
        global seconds
        node.send_to = send_to_who
        node.addr_temp = node.addr
        node.set(node.freq, node.send_to, node.power, node.rssi)
        node.send("CPU Temperature:" + str(get_cpu_temp()) + " C")
        time.sleep(0.2)
        node.set(node.freq, node.addr_temp, node.power, node.rssi)
        timer_task = Timer(seconds, send_cpu_continue, (node, send_to_who,))
        timer_task.start()
    else:
        node.send_to = send_to_who
        node.addr_temp = node.addr
        node.set(node.freq, node.send_to, node.power, node.rssi)
        node.send("CPU Temperature:" + str(get_cpu_temp()) + " C")
        time.sleep(0.2)
        node.set(node.freq, node.addr_temp, node.power, node.rssi)
        timer_task.cancel()

def get_cpu_temp():
    tempFile = open("/sys/class/thermal/thermal_zone0/temp")
    cpu_temp = tempFile.read()
    tempFile.close()
    return float(cpu_temp) / 1000

def receive_data_continuously(node):
    print("Receiving data...")
    print("Press Esc to exit receive mode")
    
    while True:
        received_data = node.receive()
        
        if received_data:
            print(f"Received: {received_data}")
        
        time.sleep(0.1)

        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            c = sys.stdin.read(1)
            if c == '\x1b':
                print("Exiting receive mode.")
                break

def get_receiver_address():
    while True:
        try:
            addr_input = input("Enter receiver address (0-255): ")
            addr = int(addr_input)
            if 0 <= addr <= 255:
                return addr
            print("Address must be between 0 and 255")
        except ValueError:
            print("Please enter a valid number")

try:
    # Setup device addresses at startup
    node = setup_addresses()
    
    time.sleep(1)
    print("\nCommands:")
    print("Press Esc to exit")
    print("Press i   to send message")
    print("Press s   to send cpu temperature every 10 seconds")
    print("Press r   to receive data")

    seconds = 2

    while True:
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            c = sys.stdin.read(1)

            if c == '\x1b':  # Esc
                break
            elif c == '\x69':  # i
                send_deal(node)
            elif c == '\x73':  # s
                send_to_who = get_receiver_address()
                print("Press c to exit the send task")
                timer_task = Timer(seconds, send_cpu_continue, (node, send_to_who,))
                timer_task.start()
                
                while True:
                    if sys.stdin.read(1) == '\x63':  # c
                        timer_task.cancel()
                        print('\x1b[1A', end='\r')
                        print(" "*100)
                        print('\x1b[1A', end='\r')
                        break
            
            elif c == '\x72':  # r
                receiver_addr = get_receiver_address()
                receive_data_continuously(node)
                send_cpu_continue(node, receiver_addr, False)

except Exception as e:
    print(f"Error occurred: {e}")

finally:
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)