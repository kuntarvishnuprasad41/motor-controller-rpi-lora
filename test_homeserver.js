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

let node; // LoRa module instance
let currentAddress;
let targetAddress = 30;
let receivingDataStarted = false; // Flag to track if receiving has started

wss.on('connection', ws => {
    console.log('Client connected');

    if (!node) { // Initialize LoRa module only once per server start, if not already initialized
        console.log("[LoRa Init - homeserver] Initializing LoRa module...");
        node = new SX126X(null, 433, currentAddress, 22, false); // Use currentAddress (initially undefined, set later)
        node.beginSerial("/dev/ttyS0"); // Initialize serial port
        console.log("[LoRa Init - homeserver] Serial port initialized, waiting for address to be set."); // Log serial port init
    }

    if (node && currentAddress !== undefined && !receivingDataStarted) {
        node.set(433, currentAddress, 22, false)
            .then(() => {
                console.log(`[LoRa Init - homeserver] LoRa module configured with address: ${currentAddress}.`);
                startReceivingData(ws); // Start receiving LoRa data for this WebSocket client
                receivingDataStarted = true;
                ws.send(JSON.stringify({ type: 'status', message: 'LoRa module initialized and listening for data.' }));
            })
            .catch(error => {
                console.error("[LoRa Init - homeserver] Error configuring LoRa module:", error);
                ws.send(JSON.stringify({ type: 'error', message: 'Error configuring LoRa module. Check server console.' }));
            });
    } else if (node && receivingDataStarted) {
        ws.send(JSON.stringify({ type: 'status', message: 'LoRa module already initialized and listening for data.' }));
    } else if (node && currentAddress === undefined) {
        ws.send(JSON.stringify({ type: 'status', message: 'LoRa module ready, waiting for current address to be set.' }));
    }


    ws.on('message', message => {
        console.log("[WebSocket] Message received:", message.toString());
        try {
            const msg = JSON.parse(message.toString());
            console.log("[WebSocket] Parsed message type:", msg.type);
            if (msg.type === 'set_current_address') {
                console.log("[WebSocket] Handling set_current_address message");
                currentAddress = parseInt(msg.address);
                console.log("[WebSocket] Parsed currentAddress:", currentAddress);
                if (!isNaN(currentAddress) && currentAddress >= 0 && currentAddress <= 65535) {
                    console.log(`Current node address set to: ${currentAddress}`);
                    if (!node) { // Initialize if not already done (unlikely, but for robustness)
                        node = new SX126X(null, 433, currentAddress, 22, false);
                        node.beginSerial("/dev/ttyS0");
                    }
                    node.set(433, currentAddress, 22, false) // Re-set LoRa parameters with new address
                        .then(() => {
                            console.log(`[LoRa] LoRa module re-configured with address: ${currentAddress}`);
                            if (!receivingDataStarted) { // Start receiving only if not already started
                                startReceivingData(ws);
                                receivingDataStarted = true;
                            }
                            ws.send(JSON.stringify({ type: 'status', message: `LoRa module initialized and listening for data at address ${currentAddress}.` }));
                        })
                        .catch(error => {
                            console.error("[LoRa] Error re-configuring LoRa module:", error);
                            ws.send(JSON.stringify({ type: 'error', message: 'Error re-configuring LoRa module. Check server console.' }));
                        });

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


function send_command(command, target_address, ws) {
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
        .then(async () => {
            console.log(`Command sent to ${target_address}. Listening for immediate response...`);
            try {
                const responseData = await waitForResponse(500);
                if (responseData) {
                    ws.send(JSON.stringify({ type: 'received_data', data: `Immediate Response to Command "${command}": ${responseData}` }));
                } else {
                    ws.send(JSON.stringify({ type: 'status', message: `Command "${command}" sent, no immediate response received.` }));
                }
            } catch (receiveTimeoutError) {
                ws.send(JSON.stringify({ type: 'status', message: `Command "${command}" sent, no immediate response within timeout.` }));
            }
        })
        .catch(error => {
            console.error("Error in send_command:", error);
            ws.send(JSON.stringify({ type: 'error', message: `Error sending command "${command}": ${error.message}` }));
        });
}

function waitForResponse(timeout) {
    return new Promise((resolve, reject) => {
        let responseReceived = false;

        const responseHandler = async (data) => {
            if (responseReceived) return;
            responseReceived = true;

            node.serialPort.off('data', responseHandler);
            node.serialPort.off('error', errorHandler);

            const receivedString = data.toString('utf8');
            try {
                const response = JSON.parse(receivedString);
                resolve(JSON.stringify(response));
            } catch (parseError) {
                resolve(receivedString);
            }
        };

        const errorHandler = (err) => {
            if (responseReceived) return;
            responseReceived = true;

            node.serialPort.off('data', responseHandler);
            node.serialPort.off('error', errorHandler);
            reject(err);
        };


        node.serialPort.on('data', responseHandler);
        node.serialPort.on('error', errorHandler);

        setTimeout(() => {
            if (!responseReceived) {
                node.serialPort.off('data', responseHandler);
                node.serialPort.off('error', errorHandler);
                resolve(null);
            }
        }, timeout);
    });
}


function startReceivingData(ws) { // Modified to filter and only send replies
    if (node && node.serialPort && node.serialPort.isOpen) {
        const receiveData = async () => {
            try {
                const receivedData = await node.receive();
                if (receivedData) {
                    try {
                        const response = JSON.parse(receivedData);
                        if (response && response.reply) { // Check if it's a valid JSON with "reply"
                            ws.send(JSON.stringify({ type: 'received_data', data: `Reply: ${JSON.stringify(response)}` })); // Send only replies, indicate "Reply"
                        } else {
                            console.log("[LoRa Receive - homeserver] Received data (no reply property, not sent to client):", receivedData); // Log non-reply messages on server only
                            // Do not send to WebSocket client if no "reply" property
                        }
                    } catch (parseError) {
                        console.error("[LoRa Receive - homeserver] Error parsing JSON data (not sent to client):", parseError, receivedData); // Log JSON parsing errors on server
                        // Do not send to WebSocket client if JSON parsing fails
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