from flask import Flask, request, jsonify, render_template
import sys
import sx126x  # Your LoRa library
import time
import json
import threading

app = Flask(__name__)

# Initialize your LoRa module
current_address = 0
node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=current_address, power=22, rssi=False)  # Adjust serial port
target_address = 30  # Your target address

# Wrapper function for safe receive
def safe_receive(node):
    try:
        received_data = node.receive()
        return received_data
    except IndexError:
        print("IndexError caught in safe_receive. No data or incomplete data.")
        return None

# Threading for receiving data (non-blocking)
received_data_queue = []

def receive_data_thread():
    while True:
        received = safe_receive(node) # Use the wrapper here
        if received:
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            received_data_queue.append({"data": received, "time": current_time})
        time.sleep(0.1)  # Check for data every 100ms


receive_thread = threading.Thread(target=receive_data_thread, daemon=True)
receive_thread.start()

def send_command(command):
    try:
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
        return {"status": "success", "message": f"Command '{command}' sent."}
    except Exception as e:
        print(f"Error sending command: {e}")
        return {"status": "error", "message": f"Error sending command: {e}"}, 500


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')  # Render the HTML template

@app.route('/send_command', methods=['POST'])
def handle_command():
    data = request.get_json()
    command = data.get('command')

    if command in ["ON", "OFF", "STATUS"]:
        result = send_command(command)
        return jsonify(result), result.get("status") == "success" and 200 or result.get("status", 500)
    else:
        return jsonify({"status": "error", "message": "Invalid command."}), 400

@app.route('/receive_data', methods=['GET'])
def receive_data():
    global received_data_queue
    data_to_send = []

    for _ in range(5):  # Try a few times to receive data
        received = safe_receive(node) # Use the wrapper here
        if received:
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            data_to_send.append({"data": received, "time": current_time})
        time.sleep(0.2)  # Small delay

    if data_to_send:
        received_data_queue.extend(data_to_send)
        data_to_send = received_data_queue[:]
        received_data_queue = []
        return jsonify(data_to_send)
    else:
        return jsonify([]) # Return empty if nothing received



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') # host='0.0.0.0' for external access