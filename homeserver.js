const WebSocket = require('ws');
const SX126x = require('./sx126x'); // Assuming sx126x.js is in the same directory

const portname = process.argv[2] || '/dev/ttyS0';
const FREQUENCY = 433;
const CURRENT_ADDRESS = 0;
const TARGET_ADDRESS = 30;
const POWER = 22;
const RSSI = true; // Enable RSSI reporting

const wss = new WebSocket.Server({ port: 8080 });

let loraModule;

async function initializeLora() {
    loraModule = new SX126x(portname, FREQUENCY, CURRENT_ADDRESS, POWER, RSSI);
    const success = await loraModule.initialize();
    if (!success) {
        console.error("Lora module initialization failed. Exiting...");
        process.exit(1); // Or handle the error as needed
    }
    console.log("Lora module initialized successfully.");
}


async function sendLoRaMessage(message, targetAddress) {
    try {
        await loraModule.send(message);
        console.log(`Sent: ${message} to ${targetAddress}`);
    } catch (error) {
        console.error("Error sending LoRa message:", error);
    }
}

wss.on('connection', ws => {
    console.log('Client connected');

    ws.on('message', async message => {
        try {
            const data = JSON.parse(message);
            console.log('Received from client:', data);

            if (data.command) {
                await sendLoRaMessage(
                    JSON.stringify({ command: data.command, time: new Date().toISOString() }),
                    TARGET_ADDRESS
                );
            }
        } catch (error) {
            console.error('Invalid JSON received:', error);
        }
    });

    ws.on('close', () => console.log('Client disconnected'));
});

async function receiveLoRaMessage() {
    try {
        const receivedData = await loraModule.receive();
        if (receivedData) {
            const currentTime = new Date().toISOString();
            console.log(`[${currentTime}] Received from LoRa:`, receivedData);

            wss.clients.forEach(client => {
                if (client.readyState === WebSocket.OPEN) {
                    client.send(JSON.stringify({ time: currentTime, message: receivedData }));
                }
            });
        }
    } catch (error) {
        console.error("Error receiving LoRa message:", error);
    }
    // Continuously listen for new messages
    setTimeout(receiveLoRaMessage, 10); // Check for new messages every 10ms
}


async function cleanup() {
    if (loraModule) {
        await loraModule.cleanup();
        console.log("Lora module cleaned up.");
    }
}

process.on('SIGINT', cleanup); // Clean up on Ctrl+C

console.log('WebSocket server and LoRa listener started...');

(async () => {
    await initializeLora();
    await receiveLoRaMessage(); // Start listening for messages
})();