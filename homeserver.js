const WebSocket = require('ws');
const { SerialPort } = require('serialport');
const { ReadlineParser } = require('@serialport/parser-readline');

const portname = process.argv[2] || '/dev/ttyS0';
const BAUD_RATE = 9600;
const FREQUENCY = 433;
const CURRENT_ADDRESS = 0;
const TARGET_ADDRESS = 30;
const POWER = 22;

const myPort = new SerialPort({ path: portname, baudRate: BAUD_RATE });
const parser = myPort.pipe(new ReadlineParser({ delimiter: '\r\n' }));

const wss = new WebSocket.Server({ port: 8080 });

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function setAddress(address) {
    console.log(`Setting address to: ${address}`);
    myPort.write(`AT+ADDRESS=${address}\r\n`);
    await delay(100);  // Ensure it takes effect
}

async function setTargetAddress(targetAddress) {
    console.log(`Setting target address to: ${targetAddress}`);
    myPort.write(`AT+DEST=${targetAddress}\r\n`);
    await delay(100);  // Allow time for setting to apply
}

async function setFrequency(freq) {
    console.log(`Setting frequency to: ${freq}`);
    myPort.write(`AT+FREQ=${freq}\r\n`);
    await delay(100); // Wait before proceeding
}

async function sendLoRaMessage(message, targetAddress) {
    console.log(`Preparing to send to ${targetAddress}: ${message}`);

    // Ensure target is set
    await setTargetAddress(targetAddress);

    await delay(200); // Small delay to allow setting to take effect

    console.log(`Sending: ${message} to ${targetAddress}`);
    myPort.write(`AT+SEND=${targetAddress},${Buffer.byteLength(message)},${message}\r\n`);

    await delay(200);  // Allow sending time before resetting back
    await setAddress(CURRENT_ADDRESS);
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

parser.on('data', data => {
    const currentTime = new Date().toISOString();
    console.log(`[${currentTime}] Received from LoRa: ${data}`);

    wss.clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
            client.send(JSON.stringify({ time: currentTime, message: data }));
        }
    });
});

myPort.on('error', err => console.error('SerialPort Error:', err.message));

console.log('WebSocket server and Serial port listener started...');
(async () => {
    await setFrequency(FREQUENCY);
    await setAddress(CURRENT_ADDRESS);
})();
