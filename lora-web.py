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
        print(f"Received data: {received_data}") # Debugging: Print received data

        return received_data
    except IndexError:
        print("IndexError caught in safe_receive. No data or incomplete data.")
        return None
    except Exception as e:  # Catch other potential errors
        print(f"An unexpected error occurred in safe_receive: {e}")
        return None

# Threading for receiving data (non-blocking)
received_data_queue =[]
queue_lock = threading.Lock()  # Create a thread lock

def receive_data_thread():
    while True:
        received = safe_receive(node)
        if received:
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            with queue_lock:  # Acquire the lock before modifying the queue
                received_data_queue.append({"data": received, "time": current_time})
            #print(f"Received data: {received}") # Debugging: Print received data
        time.sleep(0.05)  # Reduce delay for faster checks (experiment)

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
    data_to_send =[]

    with queue_lock:  # Lock during data retrieval and clearing
        data_to_send = received_data_queue[:]
        received_data_queue = [] # Clear the queue after sending data

    return jsonify(data_to_send)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # host='0.0.0.0' for external access