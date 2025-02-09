const WebSocket = require('ws');
const serialport = require('serialport');
const SerialPort = serialport.SerialPort;
const Readline = require('@serialport/parser-readline');
const portname = process.argv[2];


// --- Configuration ---
const SERIAL_PORT = '/dev/ttyS0'; //  Change this to your serial port
const BAUD_RATE = 9600;          // Adjust if necessary
const FREQUENCY = 433;          // Your LoRa frequency
const CURRENT_ADDRESS = 0;
const TARGET_ADDRESS = 30;     // Default target, can be changed by frontend
const POWER = 22;

// --- Serial Port Setup ---
const myPort = new SerialPort({
    path: portname,
    baudRate: BAUD_RATE,
    parser: new Readline("\n")
});
// const port = new SerialPort(SERIAL_PORT, { baudRate: BAUD_RATE });
const parser = port.pipe(new Readline({ delimiter: '\r\n' }));

// --- WebSocket Server Setup ---
const wss = new WebSocket.Server({ port: 8080 });

// --- LoRa Module Emulation (Replace with sx126x equivalent) ---
// --- You may need to adjust commands based on your library/hardware ---

function setAddress(address) {
    console.log(`Setting address to: ${address}`);
    // Send commands to the serial port to set the address
    // Example: (Adapt to your specific library)
    port.write(`AT+ADDRESS=${address}\r\n`);
}

function setFrequency(freq) {
    console.log(`Setting frequency to: ${freq}`);
    port.write(`AT+FREQ=${freq}\r\n`);
}

function sendLoRaMessage(message, targetAddress) {
    setAddress(targetAddress);
    console.log(`Sending to ${targetAddress}: ${message}`);
    port.write(message + '\r\n');
    setAddress(CURRENT_ADDRESS); // Reset to current address

}



// --- WebSocket Connection Handling ---
wss.on('connection', ws => {
    console.log('Client connected');

    ws.on('message', message => {
        try {
            const data = JSON.parse(message);
            console.log('Received from client:', data);

            if (data.command) {
                const target = data.targetAddress || TARGET_ADDRESS; // Use provided target or default
                sendLoRaMessage(JSON.stringify({ command: data.command, time: new Date().toISOString() }), target);
            }
        } catch (error) {
            console.error('Invalid JSON received:', error);
        }
    });

    ws.on('close', () => {
        console.log('Client disconnected');
    });
});


// --- Serial Port Data Handling ---
parser.on('data', data => {
    const currentTime = new Date().toISOString();
    const receivedData = { time: currentTime, message: data };
    console.log(`[${currentTime}] Received from LoRa: ${data}`);

    // Send received data to all connected WebSocket clients
    wss.clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
            client.send(JSON.stringify(receivedData));
        }
    });
});

port.on('error', function (err) {
    console.error('SerialPort Error: ', err.message);
});

console.log('WebSocket server and Serial port listener started...');
setFrequency(FREQUENCY);
setAddress(CURRENT_ADDRESS);