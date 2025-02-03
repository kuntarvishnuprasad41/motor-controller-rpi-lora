import sys
import sx126x
import time
import termios
import tty
import asyncio
import websockets

# Terminal settings (if needed)
old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())

# Initialize LoRa module
node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=0, power=22, rssi=False)

connected_clients = set()

async def lora_receiver():
    """Receive data from LoRa and broadcast to all WebSocket clients."""
    while True:
        try:
            # Run blocking receive in a thread to avoid blocking the event loop
            data = await asyncio.get_event_loop().run_in_executor(None, node.receive)
            if data:
                current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                message = f"[{current_time}] {data}"
                print(f"LoRa Received: {message}")

                await websocket.send(message) 
                
                # Send to all connected WebSocket clients
                for websocket in connected_clients.copy():
                    try:
                        print(f"LoRa Received: -----------|||||||||||||\\-")
                        await websocket.send(message)  # This line might be raising an exception
                        print(f"LoRa Received: ------------")
                    except websockets.exceptions.ConnectionClosed as e:
                        print(f"WebSocket connection closed: {e}")
                        connected_clients.remove(websocket)
                    except Exception as e:
                        print(f"Unexpected error sending message: {e}")
                        connected_clients.remove(websocket)
        except Exception as e:
            print(f"LoRa Error: {e}")
            await asyncio.sleep(1)  # Prevent tight loop on errors

async def websocket_handler(websocket, path=None):  # <-- KEY FIX: ADD 'path' PARAMETER
    """Handle new WebSocket connections and maintain client list."""
    connected_clients.add(websocket)
    try:
        await websocket.wait_closed()  # Keep connection open
    finally:
        connected_clients.remove(websocket)

async def main():
    # Start the LoRa receiver task
    asyncio.create_task(lora_receiver())
    
    # Start WebSocket server
    server = await websockets.serve(websocket_handler, "0.0.0.0", 8765)
    print("WebSocket server running on ws://0.0.0.0:8765")
    
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())