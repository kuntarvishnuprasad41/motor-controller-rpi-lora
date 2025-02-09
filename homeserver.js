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

function setAddress(address) {
    console.log(`Setting address to: ${address}`);
    myPort.write(`AT+ADDRESS=${address}\r\n`);
}

function setTargetAddress(targetAddress) {
    // Command to set the target address (depends on your LoRa module)
    const command = `AT+DEST=${targetAddress}\r\n`;

    console.log(`Setting target address to: ${targetAddress}`);
    myPort.write(command);
}


function setFrequency(freq) {
    console.log(`Setting frequency to: ${freq}`);
    myPort.write(`AT+FREQ=${freq}\r\n`);
}

function sendLoRaMessage(message, targetAddress) {
    console.log(`Sending to ${targetAddress}: ${message}`);
    
    // setAddress(targetAddress);
        setTargetAddress(targetAddress); // Use a function that only modifies the recipient


    

    console.log(`Sending to ${targetAddress}: ${message} from ${CURRENT_ADDRESS}`);
    myPort.write(message + '\r\n');
    setAddress(CURRENT_ADDRESS);
}

wss.on('connection', ws => {
    console.log('Client connected');

    ws.on('message', message => {
        try {
            const data = JSON.parse(message);
            console.log('Received from client:', data);

            if (data.command) {
                const target =  TARGET_ADDRESS;
                sendLoRaMessage(JSON.stringify({ command: data.command, time: new Date().toISOString() }), target);
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
setFrequency(FREQUENCY);
setAddress(CURRENT_ADDRESS);