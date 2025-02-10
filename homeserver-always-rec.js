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
let receivingDataStarted = false;

wss.on('connection', ws => {
    console.log('Client connected');

    ws.on('message', message => {
        console.log("[WebSocket] Message received:", message.toString()); // Log received message
        try {
            const msg = JSON.parse(message.toString());
            console.log("[WebSocket] Parsed message type:", msg.type); // Log parsed message type
            if (msg.type === 'set_current_address') {
                console.log("[WebSocket] Handling set_current_address message"); // Log entering this block
                currentAddress = parseInt(msg.address);
                console.log("[WebSocket] Parsed currentAddress:", currentAddress); // Log parsed address
                if (!isNaN(currentAddress) && currentAddress >= 0 && currentAddress <= 65535) {
                    console.log(`Current node address set to: ${currentAddress}`);
                    node = new SX126X(null, 433, currentAddress, 22, false);
                    node.beginSerial("/dev/ttyS0");
                    node.set(433, currentAddress, 22, false);
                    console.log("[WebSocket] Calling startReceivingData(ws)"); // Log before calling startReceivingData
                    startReceivingData(ws);
                    receivingDataStarted = true;
                    ws.send(JSON.stringify({ type: 'status', message: 'LoRa module initialized and listening for data.' }));
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
                    send_command(msg.command, targetAddress, ws);
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


function send_command(command, target_address, ws) { // Added 'ws' parameter to send response back to client
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
        .then(async () => { // Added immediate receive here
            console.log(`Command sent to ${target_address}. Listening for immediate response...`);
            try {
                const responseData = await waitForResponse(500); // Wait for response for max 500ms
                if (responseData) {
                    ws.send(JSON.stringify({ type: 'received_data', data: `Immediate Response to Command "${command}": ${responseData}` })); // Send immediate response
                } else {
                    ws.send(JSON.stringify({ type: 'status', message: `Command "${command}" sent, no immediate response received.` })); // Indicate no immediate response
                }
            } catch (receiveTimeoutError) {
                ws.send(JSON.stringify({ type: 'status', message: `Command "${command}" sent, no immediate response within timeout.` })); // Indicate timeout
            }
        })
        .catch(error => {
            console.error("Error in send_command:", error);
            ws.send(JSON.stringify({ type: 'error', message: `Error sending command "${command}": ${error.message}` })); // Send error to client
        });
}

function waitForResponse(timeout) { // Function to wait for a response with a timeout
    return new Promise((resolve, reject) => {
        let responseReceived = false;

        const responseHandler = async (data) => {
            if (responseReceived) return; // Prevent handling multiple responses if they arrive quickly
            responseReceived = true;

            node.serialPort.off('data', responseHandler); // Remove data listener
            node.serialPort.off('error', errorHandler); // Remove error listener

            const receivedString = data.toString('utf8');
            try {
                const response = JSON.parse(receivedString);
                resolve(JSON.stringify(response)); // Resolve with JSON response
            } catch (parseError) {
                resolve(receivedString); // Resolve with raw string if JSON parsing fails
            }
        };

        const errorHandler = (err) => {
            if (responseReceived) return;
            responseReceived = true;

            node.serialPort.off('data', responseHandler); // Remove data listener
            node.serialPort.off('error', errorHandler); // Remove error listener
            reject(err);
        };


        node.serialPort.on('data', responseHandler);
        node.serialPort.on('error', errorHandler);

        setTimeout(() => {
            if (!responseReceived) {
                node.serialPort.off('data', responseHandler); // Timeout - remove listener
                node.serialPort.off('error', errorHandler); // Remove error listener
                resolve(null); // Resolve with null to indicate no response within timeout
            }
        }, timeout); // Timeout after 'timeout' milliseconds
    });
}


function startReceivingData(ws) { // Function to start continuous receiving (background)
    if (node && node.serialPort && node.serialPort.isOpen) {
        const receiveData = async () => {
            try {
                const receivedData = await node.receive();
                if (receivedData) {
                    try {
                        const response = JSON.parse(receivedData);
                        if (response && response.reply) {
                            ws.send(JSON.stringify({ type: 'received_data', data: `Background Message: ${JSON.stringify(response)}` })); // Indicate background message
                        } else {
                            ws.send(JSON.stringify({ type: 'received_data', data: `Background Message: ${receivedData}` })); // Indicate background message
                        }
                    } catch (parseError) {
                        console.error("Error parsing received JSON data (background):", parseError);
                        ws.send(JSON.stringify({ type: 'received_data', data: `Background Message (Unparsed): ${receivedData}` })); // Indicate background unparsed
                    }
                }
            } catch (receiveError) {
                console.error("Error receiving data (background):", receiveError);
                ws.send(JSON.stringify({ type: 'error', message: 'Error receiving data from LoRa module in background.' }));
            }
            receiveData();
        };
        receiveData();
    } else {
        console.error("Serial port not initialized or not open for background receiving.");
        ws.send(JSON.stringify({ type: 'error', message: 'Serial port not ready for background data reception.' }));
    }
}


app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});


const PORT = 3000;
server.listen(PORT, () => {
    console.log(`Server started on http://192.168.100.16:${PORT}`);
});