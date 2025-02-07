from flask import Flask, request, jsonify, render_template
import sys
import sx126x
import time
import json
import threading

app = Flask(__name__)

# Initialize your LoRa module
current_address = 0
node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=current_address, power=22, rssi=False)  # Adjust serial port
target_address = 30  # Your target address

# Wrapper function for safe receive with address filtering and retries
def safe_receive(node, max_retries=3):
    for _ in range(max_retries):
        try:
            received_data = node.receive()  # Receive data first
            if received_data:  # Check if data was received (not None)
                try:
                    # Attempt to decode to get the address (if it's part of the message)
                    decoded_data = received_data.decode('utf-8')
                    received_json = json.loads(decoded_data) # Parse JSON to access the address
                    received_address = received_json.get('address') # Assumes 'address' key in JSON
                    print(f"Received message (potentially) from address: {received_address}")

                    if received_address!= target_address and received_address is not None:  # Filter by address
                        print("Message discarded: Wrong address")
                        return None  # Discard if not for us
                    return received_data # If it is for us, return

                except (UnicodeDecodeError, json.JSONDecodeError) as e:
                    print(f"Error decoding or parsing JSON: {e}. Raw data: {received_data}")
                    return None # Discard if JSON format is incorrect.
            time.sleep(0.02)  # Small delay before retrying
            continue # Retry if no data
        except IndexError:  # Keep this for general receive errors
            print("IndexError caught in safe_receive. No data or incomplete data.")
            time.sleep(0.02)  # Small delay before retrying
            continue  # Retry
        except Exception as e:
            print(f"An unexpected error occurred in safe_receive: {e}")
            return None
    return None  # Return None if all retries fail


# Threading for receiving data (non-blocking)
received_data_queue = []
queue_lock = threading.Lock()  # Create a thread lock
data_received_condition = threading.Condition(queue_lock)  # Condition variable

def receive_data_thread():
    while True:
        with data_received_condition:  # Acquire the condition lock
            received = safe_receive(node)
            if received:
                current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                received_data_queue.append({"data": received, "time": current_time})
                data_received_condition.notify()  # Notify waiting threads that data is available
            data_received_condition.wait(0.1)  # Wait with a timeout

receive_thread = threading.Thread(target=receive_data_thread, daemon=True)
receive_thread.start()
g.Thread(target=receive_data_thread, daemon=True)
receive_thread.start()

def send_command(command):
    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        message = {"command": command, "time": timestamp, "address": current_address} # Include the address
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

    with data_received_condition:  # Acquire the condition lock
        if not received_data_queue:  # Check if the queue is empty
            data_received_condition.wait(1)  # Wait for data with a timeout of 1 second

        # If data is available or timeout occurs, retrieve and clear the queue
        data_to_send = received_data_queue[:]
        received_data_queue = []

    return jsonify(data_to_send)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # host='0.0.0.0' for external access