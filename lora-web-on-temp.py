import sys
import sx126x  # Your LoRa library
import time
import json
from flask import Flask, render_template, request

# ... (Your existing LoRa initialization code) ...
current_address = 0  # Or get it from user input
node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=current_address, power=22, rssi=False)

app = Flask(__name__)

def send_command(command, target_address):
    """Sends a command (same as your original function)."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    message = {"command": command, "time": timestamp}
    json_message = json.dumps(message)

    original_address = node.addr
    node.addr_temp = node.addr
    node.set(node.freq, target_address, node.power, node.rssi)
    node.send(json_message)
    node.set(node.freq, original_address, node.power, node.rssi)
    time.sleep(0.2)
    print(f"Command sent to {target_address}.")


@app.route("/", methods=["GET", "POST"])
def index():
    message = None  # Initialize message
    if request.method == "POST":
        command = request.form.get("command")
        try:  # Handle potential errors
            target_address = int(request.form.get("target_address"))
            if 0 <= target_address <= 65535:  # Validate input
                send_command(command, target_address)
                message = f"Command '{command}' sent to {target_address}."
            else:
                message = "Invalid target address. Must be between 0 and 65535."
        except ValueError:
            message = "Invalid target address. Please enter a number."
        except Exception as e: # Catch any LoRa related error
            message = f"An error occurred: {e}"

    # Check for incoming LoRa messages (non-blocking)
    received_data = node.receive()
    if received_data:
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print(f"[{current_time}] Received: {received_data}")
        # Add received data to be displayed on webpage if needed.
        if message:
            message += f"<br>[{current_time}] Received: {received_data}" #Append to existing message.
        else:
             message = f"[{current_time}] Received: {received_data}"

    return render_template("index.html", message=message)  # Pass message to template


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0') # Make accessible on your network. Debug only for development!