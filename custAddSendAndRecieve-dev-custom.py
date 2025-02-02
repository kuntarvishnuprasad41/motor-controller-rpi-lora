import sys
import sx126x
import threading
import time
import termios
import tty

# Setup terminal for capturing input
old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())

# Function to read user input for device address
def read_device_address():
    while True:
        try:
            return int(input("Enter the current device address (1-255): "))
        except ValueError:
            print("Invalid input. Please enter a valid integer.")

# Initialize the SX126x node
node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=0, power=22, rssi=False)

# Function to receive data continuously
def receive_data():
    while True:
        # Attempt to receive data
        try:
            received_data = node.receive()
            if received_data:  # Check if data is received
                print(f"Received data from address {node.rx_addr}: {received_data}")
        except Exception as e:
            print(f"Error receiving data: {e}")
        time.sleep(0.1)

# Function to send data continuously
def send_data(destination_address):
    while True:
        # Send temperature to destination address
        node.set(node.freq, destination_address, node.power, node.rssi)
        node.send("CPU Temperature: " + str(get_cpu_temp()) + " C")
        time.sleep(2)  # Sending every 2 seconds

# Function to get CPU temperature
def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as temp_file:
            cpu_temp = temp_file.read()
            return float(cpu_temp) / 1000
    except Exception as e:
        print(f"Error reading CPU temperature: {e}")
        return 0.0

# Main program logic
try:
    # Get current device address
    current_device_address = read_device_address()
    print(f"Current device address: {current_device_address}")

    # Set device address
    node.addr = current_device_address
    node.set(node.freq, node.addr, node.power, node.rssi)

    # Ask for the destination address
    destination_address = int(input("Enter the destination address (1-255): "))
    print(f"Sending and receiving data to/from address {destination_address}")

    # Start receiving data in a separate thread
    receive_thread = threading.Thread(target=receive_data)
    receive_thread.daemon = True  # This allows the thread to exit when the program exits
    receive_thread.start()

    # Start sending data to the destination address
    send_data(destination_address)

except KeyboardInterrupt:
    print("\nProgram interrupted by user.")
finally:
    # Reset terminal settings
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
