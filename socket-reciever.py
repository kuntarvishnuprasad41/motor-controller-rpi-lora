#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import sx126x
import time
import select
import termios
import tty
import asyncio
import websockets

# Terminal settings
old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())

# Initialize LoRa module
node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=0, power=22, rssi=False)

async def send_data(websocket, path):
    try:
        while True:
            received_data = node.receive()

            if received_data:
                current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                message = f"[{current_time}] {received_data}"
                print(message)

                # Send data to WebSocket client
                await websocket.send(message)

            await asyncio.sleep(0.1)  # Prevent CPU overuse

    except Exception as e:
        print(f"Error: {e}")

# Start WebSocket server
start_server = websockets.serve(send_data, "0.0.0.0", 8765)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
