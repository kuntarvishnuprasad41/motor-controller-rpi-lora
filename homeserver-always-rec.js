const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const path = require('path');

const SX126X = require('./sx126x');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());

let node;
let currentAddress;
let targetAddress = 30;
let receivingDataStarted = false; // Flag to track if receiving has started

wss.on('connection', ws => {
    console.log('Client connected');

    ws.on('message', message => {
        try {
            const msg = JSON.parse(message.toString());
            if (msg.type === 'set_current_address') {
                currentAddress = parseInt(msg.address);
                if (!isNaN(currentAddress) && currentAddress >= 0 && currentAddress <= 65535) {
                    console.log(`Current node address set to: ${currentAddress}`);
                    node = new SX126X(null, 433, currentAddress, 22, false);
                    node.beginSerial("/dev/ttyS0");
                    node.set(433, currentAddress, 22, false);

                    if (!receivingDataStarted) { // Start receiving data only once after address is set
                        startReceivingData(ws);
                        receivingDataStarted = true;
                        ws.send(JSON.stringify({ type: 'status', message: 'LoRa module initialized and listening for data.' }));
                    } else {
                        ws.send(JSON.stringify({ type: 'status', message: 'LoRa module re-initialized.' })); // If address is reset, just re-initialize status
                    }

                } else {
                    ws.send(JSON.stringify({ type: 'error', message: 'Invalid current address.' }));
                }
            } else if (msg.type === 'set_target_address') {
                targetAddress = parseInt(msg.address);
                if (!isNaN(targetAddress) && targetAddress >= 0 && targetAddress <= 65535) {
                    console.log(`Target node address set to: ${targetAddress}`);
                    ws.send(JSON.stringify({ type: 'status', message: `Target address updated to ${targetAddress}` }));
                } else {
                    ws.send(JSON.stringify({ type: 'error', message: 'Invalid target address.' }));
                }
            } else if (msg.type === 'command') {
                if (node) {
                    send_command(msg.command, targetAddress);
                    ws.send(JSON.stringify({ type: 'status', message: `Command "${msg.command}" sent to ${targetAddress}` }));
                } else {
                    ws.send(JSON.stringify({ type: 'error', message: 'LoRa module not initialized. Set current address first.' }));
                }
            }
        } catch (e) {
            console.error('Error parsing message:', e);
            ws.send(JSON.stringify({ type: 'error', message: 'Invalid message format.' }));
        }
    });

    ws.on('close', () => {
        console.log('Client disconnected');
    });

    ws.on('error', error => {
        console.error('WebSocket error:', error);
    });
});


function send_command(command, target_address) {
    if (!node) {
        console.error("LoRa module not initialized.");
        return;
    }
    const timestamp = new Date().toISOString().replace(/T/, ' ').replace(/\..+/, '');
    const message = { command: command, time: timestamp };
    const json_message = JSON.stringify(message);

    const original_address = node.addr;
    node.addr_temp = node.addr;
    node.set(node.freq, target_address, node.power, node.rssi)
        .then(() => {
            node.send(json_message);
            return new Promise(resolve => setTimeout(resolve, 200));
        })
        .then(() => {
            return node.set(node.freq, original_address, node.power, node.rssi);
        })
        .then(() => {
            console.log(`Command sent to ${target_address}.`);
        })
        .catch(error => {
            console.error("Error in send_command:", error);
        });
}


function startReceivingData(ws) { // Function to start receiving data and send to WebSocket
    if (node && node.serialPort && node.serialPort.isOpen) {
        const receiveData = async () => {
            try {
                const receivedData = await node.receive();
                if (receivedData) {
                    try {
                        const response = JSON.parse(receivedData); // Try to parse as JSON
                        if (response && response.reply) {
                            ws.send(JSON.stringify({ type: 'received_data', data: JSON.stringify(response) })); // Send JSON response to client
                        } else {
                            ws.send(JSON.stringify({ type: 'received_data', data: receivedData })); // Send raw data if not in expected JSON format
                        }
                    } catch (parseError) {
                        console.error("Error parsing received JSON data:", parseError);
                        ws.send(JSON.stringify({ type: 'received_data', data: receivedData })); // Send raw data if JSON parsing fails
                    }
                }
            } catch (receiveError) {
                console.error("Error receiving data:", receiveError);
                ws.send(JSON.stringify({ type: 'error', message: 'Error receiving data from LoRa module.' }));
            }
            receiveData(); // Call receiveData again to continuously listen
        };
        receiveData(); // Initial call to start the loop
    } else {
        console.error("Serial port not initialized or not open for receiving.");
        ws.send(JSON.stringify({ type: 'error', message: 'Serial port not ready to receive data.' }));
    }
}


app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});


const PORT = 3000;
server.listen(PORT, () => {
    console.log(`Server started on http://192.168.100.16:${PORT}`);
});