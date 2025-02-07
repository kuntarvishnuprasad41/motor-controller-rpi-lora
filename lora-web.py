from flask import Flask, request, jsonify, render_template
import sys
import sx126x
import time
import json
import threading

app = Flask(__name__)

# Initialize your LoRa module
current_address = 0
node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=current_address, power=22, rssi=True)  # rssi=True for RSSI
target_address = 30  # Your target address

# Lock for LoRa operations to prevent conflicts
lora_lock = threading.Lock()

def safe_receive(node, max_retries=3):  # Reduced retries
    for _ in range(max_retries):
        with lora_lock:  # Acquire lock for LoRa receive
            # received_data = node.receive()
            # if received_data!=None:
            #     print(f"Received in lora: {received_data}")
            try:
                received_data = node.receive()
                if received_data!=None:
                    print(f"Received in lora: {received_data}")
                # if received_data:
                #     try:
                #         received_json = json.loads(received_data)
                #         received_address = received_json.get('address')
                #         if received_address != target_address:
                #             print("Message discarded: Wrong address")
                #             return None
                #         return received_data
                #     except json.JSONDecodeError as e:
                #         print(f"JSON decode error: {e}. Raw: {received_data}")
                #         return None
                time.sleep(0.01)  # Shorter delay
            except Exception as e:
                print(f"Receive error: {e}")
                
                return None
    return None

received_data_queue = []
data_received_condition = threading.Condition()

def receive_data_thread():
    while True:
        received = safe_receive(node)
        if received:
            with data_received_condition:
                current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                received_data_queue.append({"data": received, "time": current_time})
                data_received_condition.notify()
        time.sleep(0.01)  # Shorter loop delay

receive_thread = threading.Thread(target=receive_data_thread, daemon=True)
receive_thread.start()

def send_command(command):
    with lora_lock:  # Acquire lock for LoRa send
        try:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            message = {"command": command, "time": timestamp, "address": current_address}
            json_message = json.dumps(message)

            original_address = node.addr
            node.addr_temp = node.addr
            node.set(node.freq, target_address, node.power, node.rssi)
            node.send(json_message)
            node.set(node.freq, original_address, node.power, node.rssi)
            time.sleep(0.1)  # Delay after send
            print(f"Command '{command}' sent to {target_address}.")
            return {"status": "success", "message": f"Command '{command}' sent."}
        except Exception as e:
            print(f"Send error: {e}")
            return {"status": "error", "message": f"Error sending command: {e}"}, 500

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/send_command', methods=['POST'])
def handle_command():
    data = request.get_json()
    command = data.get('command')
    if command in ["ON", "OFF", "STATUS"]:
        return jsonify(send_command(command))
    else:
        return jsonify({"status": "error", "message": "Invalid command."}), 400


@app.route('/receive_data', methods=['GET'])
def receive_data():
    global received_data_queue
    with data_received_condition:
        if not received_data_queue:
            data_received_condition.wait(0.5)
        data_to_send = received_data_queue[:]
        received_data_queue = []

    processed_data =  []# List to hold processed messages
    for item in data_to_send:
        received = item["data"]
        processed_message = process_received_data(node, received) #Pass received data to the new function
        if processed_message:
            item["data"] = processed_message  # Update the queue with the processed JSON
            processed_data.append(item) # Append the processed items

    return jsonify(processed_data)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')