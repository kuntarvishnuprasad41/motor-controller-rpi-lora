const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const path = require('path');

const SX126X = require('./sx126x'); // Import SX126X

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

app.use(express.static(path.join(__dirname, 'public')));

let node; // LoRa module instance - define it here
let currentAddress = 0; // Default current address for test server
let receivingDataStarted = false; // Flag to track if receiving has started

// Function to start continuous receiving of LoRa data
function startReceivingData(ws) {
    if (node && node.serialPort && node.serialPort.isOpen) {
        const receiveData = async () => {
            try {
                const receivedData = await node.receive();
                if (receivedData) {
                    console.log("[LoRa Receive - test_homeserver] Received LoRa data:", receivedData); // Log LoRa data on server
                    ws.send(JSON.stringify({ type: 'lora_data', data: receivedData })); // Send LoRa data to WebSocket client
                }
            } catch (receiveError) {
                console.error("[LoRa Receive - test_homeserver] Error receiving LoRa data:", receiveError);
                ws.send(JSON.stringify({ type: 'error', message: 'Error receiving LoRa data from module.' }));
            }
            receiveData(); // Continue listening
        };
        receiveData(); // Start the loop
    } else {
        console.error("[LoRa Receive - test_homeserver] Serial port not initialized or not open for receiving.");
        ws.send(JSON.stringify({ type: 'error', message: 'Serial port not ready for LoRa data reception.' }));
    }
}


wss.on('connection', ws => {
    console.log('Client connected');

    if (!node) { // Initialize LoRa module only once per server start, if not already initialized
        console.log("[LoRa Init - test_homeserver] Initializing LoRa module...");
        node = new SX126X(null, 433, currentAddress, 22, false); // Use default currentAddress 0 for test server
        node.beginSerial("/dev/ttyS0"); // Initialize serial port
        node.set(433, currentAddress, 22, false)
            .then(() => {
                console.log("[LoRa Init - test_homeserver] LoRa module initialized and configured.");
                if (!receivingDataStarted) {
                    startReceivingData(ws); // Start receiving LoRa data for this WebSocket client
                    receivingDataStarted = true;
                    ws.send(JSON.stringify({ type: 'status', message: 'LoRa module initialized and listening for data.' }));
                }
            })
            .catch(error => {
                console.error("[LoRa Init - test_homeserver] Error initializing LoRa module:", error);
                ws.send(JSON.stringify({ type: 'error', message: 'Error initializing LoRa module. Check server console.' }));
            });
    } else {
        if (!receivingDataStarted) { // In case a client connects after initial setup
            startReceivingData(ws);
            receivingDataStarted = true;
        }
        ws.send(JSON.stringify({ type: 'status', message: 'LoRa module already initialized and listening for data.' }));
    }


    ws.on('message', message => {
        console.log('[WebSocket Server - test_homeserver] Received message:', message.toString()); // Log message on server
        try {
            const msg = JSON.parse(message.toString());
            if (msg.type === 'test') {
                console.log('[WebSocket Server - test_homeserver] Test message received, sending reply.');
                ws.send(JSON.stringify({ type: 'test_reply', message: 'Hello from server!' }));
            }
        } catch (e) {
            console.error('Error parsing message:', e);
        }
    });

    ws.on('close', () => {
        console.log('Client disconnected');
    });

    ws.on('error', error => {
        console.error('WebSocket error:', error);
    });
});


app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'test_index.html')); // Serve test_index.html
});


const PORT = 3000;
server.listen(PORT, () => {
    console.log(`Server started on http://192.168.100.16:${PORT}`);
});