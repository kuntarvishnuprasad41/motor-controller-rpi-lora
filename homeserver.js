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

function sendCommand(command, targetAddress) {
    const timestamp = new Date().toISOString();
    const message = JSON.stringify({ command, time: timestamp });

    console.log(`Setting target address: ${targetAddress}`);
    myPort.write(`AT+DEST=${targetAddress}\r\n`, () => {
        setTimeout(() => {
            console.log(`Sending command: ${message}`);
            myPort.write(`AT+SEND=${targetAddress},${message.length},${message}\r\n`);
        }, 200); // Give time to switch address
    });
}

wss.on('connection', ws => {
    console.log('Client connected');

    ws.on('message', message => {
        try {
            const data = JSON.parse(message);
            console.log('Received from client:', data);

            if (data.command) {
                sendCommand(data.command, TARGET_ADDRESS);
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
setTimeout(() => myPort.write(`AT+FREQ=${FREQUENCY}\r\n`), 100);
setTimeout(() => myPort.write(`AT+ADDRESS=${CURRENT_ADDRESS}\r\n`), 200);
