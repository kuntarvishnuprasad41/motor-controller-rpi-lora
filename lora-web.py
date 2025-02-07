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
            r_buff = node.read_buffer() # Or however you get the raw buffer
            if not r_buff or len(r_buff) < 2:  # Check for empty or short buffer
                time.sleep(0.02) # Small delay before retrying
                continue # Retry if no data

            node_address = (r_buff << 8) + r_buff # Extract address
            print(f"Received message from address: {node_address}")  # Debugging

            if node_address!= target_address:  # Filter by address
                print("Message discarded: Wrong address")
                return None  # Discard if not for us

            received_data = node.receive()  # Now call receive only if the address matches
            return received_data # Success!

        except IndexError:
            print("IndexError caught in safe_receive. No data or incomplete data.")
            time.sleep(0.02) # Small delay before retrying
            continue # Retry
        except Exception as e:  # Catch other potential errors
            print(f"An unexpected error occurred in safe_receive: {e}")
            return None
    return None # Return None if all retries fail


# Threading for receiving data (non-blocking)
received_data_queue = []
queue_lock = threading.Lock()  # Create a thread lock

def receive_data_thread():
    while True:
        received = safe_receive(node)
        if received:
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            with queue_lock:  # Acquire the lock before modifying the queue
                received_data_queue.append({"data": received, "time": current_time})
        time.sleep(0.05)  # Reduce delay for faster checks (experiment)

receive_thread = threading.Thread(target=receive_data_thread, daemon=True)
receive_thread.start()

def send_command(command):
    #... (same as before)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')  # Render the HTML template

@app.route('/send_command', methods=['POST'])
def handle_command():
   #... (same as before)

@app.route('/receive_data', methods=['GET'])
def receive_data():
    global received_data_queue
    data_to_send =[]

    with queue_lock:
        for item in received_data_queue:  # Iterate through each item
            try:
                decoded_data = item['data'].decode('utf-8')  # Decode the bytes to string
                data_to_send.append({"data": decoded_data, "time": item['time']})
            except UnicodeDecodeError as e:
                print(f"Decoding error: {e}. Raw data: {item['data']}")
                data_to_send.append({"data": "Decoding Error", "time": item['time']})  # Or handle differently

        received_data_queue = [] # Clear the queue *after* processing

    return jsonify(data_to_send)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # host='0.0.0.0' for external access