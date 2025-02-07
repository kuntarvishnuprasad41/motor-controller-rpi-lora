import sys
import sx126x
import time
import select
import termios
import tty
import json

old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())

node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=30, power=22, rssi=False)

def send_command(command):
    """Sends a command with a timestamp."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    message = {"command": command, "time": timestamp}
    json_message = json.dumps(message)
    node.send(json_message)
    time.sleep(0.2)


try:
    time.sleep(1)
    print("Press \033[1;32m1\033[0m to send Motor ON command")
    print("Press \033[1;32m2\033[0m to send Motor OFF command")
    print("Press \033[1;32m3\033[0m to send Motor STATUS request")
    print("Press \033[1;32mEsc\033[0m to exit")

    while True:
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            c = sys.stdin.read(1)

            if c == '\x1b':  # Esc key
                break

            if c == '1':
                send_command("ON")
                print("Motor ON command sent.")
            elif c == '2':
                send_command("OFF")
                print("Motor OFF command sent.")
            elif c == '3':
                send_command("STATUS")
                print("Motor STATUS request sent.")

            sys.stdout.flush()

        node.receive()
        received_data = node.get_received_data()
        if received_data:
            try:
                received_message = json.loads(received_data)
                print("Received:", received_message)
            except json.JSONDecodeError:
                print("Received non-JSON data:", received_data)


except Exception as e:
    print(f"An error occurred: {e}")  # Print any exceptions
finally:
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)  # Restore terminal settings