from flask import Flask, render_template, request, jsonify
import sx126x
import time
import json

app = Flask(__name__)

# Initialize the SX126x module
current_address = 0
node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=current_address, power=22, rssi=False)

def send_command(command, target_address):
    """Sends a command to the target node."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    message = {"command": command, "time": timestamp}
    json_message = json.dumps(message)

    original_address = node.addr
    node.addr_temp = node.addr
    node.set(node.freq, target_address, node.power, node.rssi)
    node.send(json_message)
    node.set(node.freq, original_address, node.power, node.rssi)
    time.sleep(0.2)
    return f"Command '{command}' sent to {target_address}."

@app.route('/')
def index():
    """Renders the main UI."""
    return render_template('index.html')

@app.route('/send', methods=['POST'])
def send():
    """Handles sending commands from the UI."""
    data = request.json
    command = data.get('command')
    target_address = data.get('target_address', 30)  # Default target address is 30
    if command in ["ON", "OFF", "STATUS"]:
        result = send_command(command, target_address)
        return jsonify({"status": "success", "message": result})
    else:
        return jsonify({"status": "error", "message": "Invalid command"}), 400

@app.route('/receive', methods=['GET'])
def receive():
    """Handles receiving data from the SX126x module."""
    received_data = node.receive()
    if received_data:
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        return jsonify({"status": "success", "data": received_data, "time": current_time})
    else:
        return jsonify({"status": "success", "data": None})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)