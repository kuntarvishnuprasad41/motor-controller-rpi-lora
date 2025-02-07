from flask import Flask, request, jsonify, render_template
import sys
import sx126x  # Your LoRa library
import time
import json
import threading

app = Flask(__name__)

# Initialize your LoRa module (same as in your original script)
current_address = 0
node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=current_address, power=22, rssi=False)
target_address = 30  # Your target address

# Threading for receiving data (non-blocking)
received_data_queue = []
def receive_data_thread():
    while True:
        received_data = node.receive()
        if received_data:
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            received_data_queue.append({"data": received_data, "time": current_time})
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
    data_to_send = received_data_queue[:]  # Create a copy
    received_data_queue = []  # Clear the queue
    return jsonify(data_to_send)



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') # host='0.0.0.0' for external access