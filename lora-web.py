from flask import Flask, request, jsonify, render_template
import sys
import sx126x
import time
import json
import threading
import sqlite3




app = Flask(__name__)


DATABASE = 'lora_data.db'
def create_table():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lora_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT
        )
    ''')
    conn.commit()
    conn.close()

create_table() 

# Initialize your LoRa module
current_address = 0
node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=current_address, power=22, rssi=True)  # rssi=True for RSSI
target_address = 30  # Your target address

# Lock for LoRa operations to prevent conflicts

received_data_queue = []
lora_lock = threading.Lock()
data_received_condition = threading.Condition()
data_available = threading.Condition(lora_lock)  # Condition variable


def safe_receive(node, max_retries=3):
    for _ in range(max_retries):
        with lora_lock:  # Lock only for the actual receive operation
            try:
                received_data = node.receivetemp()  # Your LoRa receive function
                if received_data:
                    print(f"Received in lora: {received_data}")
                    with sqlite3.connect(DATABASE) as conn:
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO lora_messages (message) VALUES (?)", (received_data,))
                        conn.commit()
                    data_available.notify() # Signal new data in DB
                    return received_data
                time.sleep(0.01)
            except Exception as e:
                print(f"Receive error: {e}")
                return None
    return None



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



def process_received_data(node, received_data):
     
    if isinstance(received_data, dict):
        return received_data # no change needed

    try:
        # Attempt to parse the JSON string. If it's already a dict, this will raise an exception.
        data_dict = json.loads(received_data)
        return data_dict  # Return the dictionary if parsing is successful

    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {e}")
        print(f"Raw data: {received_data}")
        return None  # Return None to indicate an error

    except TypeError as e: # Handle cases where received_data might be None or not a string
        print(f"TypeError: {e}")
        print(f"Received data: {received_data}")
        return None

    except Exception as e: # Catch any other unexpected errors
        print(f"An unexpected error occurred: {e}")
        print(f"Received data: {received_data}")
        return None



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')