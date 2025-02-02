import sys
import sx126x
import time
import select
import termios
import tty
from threading import Timer

old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())

# Your previous code and imports here
node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=0, power=22, rssi=False)


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
    print(" "*100)
    print(" "*100)
    print(" "*100)
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


def get_cpu_temp():
    tempFile = open("/sys/class/thermal/thermal_zone0/temp")
    cpu_temp = tempFile.read()
    tempFile.close()
    return float(cpu_temp) / 1000

# Function to handle continuous receiving
def receive_data_continuously():
    print("Receiving data...")
    while True:
        # Attempt to receive data
        received_data = node.receive()  # Adjust this based on how the receive function works

        if received_data:
            print(f"Received: {received_data}")
        
        time.sleep(0.1)  # Short delay to avoid overloading the CPU

        # Check if the user pressed Esc to exit
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            c = sys.stdin.read(1)
            if c == '\x1b':  # If the user presses Esc, stop receiving
                print("Exiting receive mode.")
                break  # Exit the loop and stop receiving


try:
    time.sleep(1)
    print("Press Esc to exit")
    print("Press i   to send")
    print("Press s   to send cpu temperature every 10 seconds")
    print("Press r   to receive data")

    seconds = 2
    send_to_who = 30

    while True:
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            c = sys.stdin.read(1)

            # detect key Esc
            if c == '\x1b':
                break
            # detect key i
            elif c == '\x69':
                send_deal()
            # detect key s
            elif c == '\x73':
                print("Press c to exit the send task")
                timer_task = Timer(seconds, send_cpu_continue, (send_to_who,))
                timer_task.start()
                
                while True:
                    if sys.stdin.read(1) == '\x63':
                        timer_task.cancel()
                        print('\x1b[1A', end='\r')
                        print(" "*100)
                        print('\x1b[1A', end='\r')
                        break

            # detect key r to receive data
            elif c == '\x72':
                # Call the function to receive data continuously
                receive_data_continuously()

except Exception as e:
    print(f"Error occurred: {e}")

finally:
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
