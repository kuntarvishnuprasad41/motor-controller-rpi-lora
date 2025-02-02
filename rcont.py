import sys
import sx126x
import time
import select
import termios
import tty

old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())

# Your previous code and imports here
node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=0, power=22, rssi=False)

def get_cpu_temp():
    tempFile = open("/sys/class/thermal/thermal_zone0/temp")
    cpu_temp = tempFile.read()
    tempFile.close()
    return float(cpu_temp) / 1000

# Function to handle continuous receiving
def receive_data_continuously():
    print("Receiving data...")
    while True:
        node.receive()
        if node.rx_flag:  # Check if data has been received
            print(f"Received: {node.rx_data}")
            node.rx_flag = False  # Reset the flag after processing
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
