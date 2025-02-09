This is my code for sx126x  

const { Gpio } = require('onoff');
const { SerialPort } = require('serialport');
const { promisify } = require('util');
const sleep = promisify(setTimeout);

class SX126x {
    constructor(serialPath, freq, addr, power, rssi) {
        this.M0 = new Gpio(22, 'out');
        this.M1 = new Gpio(27, 'out');
        this.serialPath = serialPath;
        this.freq = freq;
        this.addr = addr;
        this.power = power;
        this.rssi = rssi;
        this.sendTo = addr;

        // Serial port configuration
        this.serial = new SerialPort({
            path: serialPath,
            baudRate: 9600,
            autoOpen: false
        });

        this.cfgReg = Buffer.from([0xC2, 0x00, 0x09, 0x00, 0x00, 0x00, 0x62, 0x00, 0x17, 0x00, 0x00, 0x00]);

        // Constants
        this.UART_BAUDRATES = {
            1200: 0x00,
            2400: 0x20,
            4800: 0x40,
            9600: 0x60,
            19200: 0x80,
            38400: 0xA0,
            57600: 0xC0,
            115200: 0xE0
        };

        this.AIR_SPEEDS = {
            300: 0x00,
            1200: 0x01,
            2400: 0x02,
            4800: 0x03,
            9600: 0x04,
            19200: 0x05,
            38400: 0x06,
            62500: 0x07
        };

        this.POWER_LEVELS = {
            22: 0x00,
            17: 0x01,
            13: 0x02,
            10: 0x03
        };

        this.BUFFER_SIZES = {
            240: 0x00,
            128: 0x40,
            64: 0x80,
            32: 0xC0
        };
    }

    async initialize() {
        try {
            // Initialize GPIO
            await this.M0.write(0);
            await this.M1.write(1);

            // Open serial port
            await new Promise((resolve, reject) => {
                this.serial.open(err => err ? reject(err) : resolve());
            });

            await this.configureModule();
            return true;
        } catch (err) {
            console.error('Initialization failed:', err);
            return false;
        }
    }

    async configureModule(
        freq = this.freq,
        addr = this.addr,
        power = this.power,
        rssi = this.rssi,
        airSpeed = 2400,
        netId = 0,
        bufferSize = 240,
        crypt = 0
    ) {
        try {
            await this.M0.write(0);
            await this.M1.write(1);
            await sleep(100);

            const lowAddr = addr & 0xFF;
            const highAddr = (addr >> 8) & 0xFF;
            const netIdTemp = netId & 0xFF;
            const freqTemp = freq > 850 ? freq - 850 : freq - 410;

            const airSpeedTemp = this.AIR_SPEEDS[airSpeed];
            const bufferSizeTemp = this.BUFFER_SIZES[bufferSize];
            const powerTemp = this.POWER_LEVELS[power];
            const rssiTemp = rssi ? 0x80 : 0x00;

            this.cfgReg[3] = highAddr;
            this.cfgReg[4] = lowAddr;
            this.cfgReg[5] = netIdTemp;
            this.cfgReg[6] = this.UART_BAUDRATES[9600] + airSpeedTemp;
            this.cfgReg[7] = bufferSizeTemp + powerTemp + 0x20;
            this.cfgReg[8] = freqTemp;
            this.cfgReg[9] = 0x03 + rssiTemp;
            this.cfgReg[10] = (crypt >> 8) & 0xFF;
            this.cfgReg[11] = crypt & 0xFF;

            let configSuccess = false;
            for (let i = 0; i < 2; i++) {
                await this.serialWrite(this.cfgReg);
                await sleep(200);

                const response = await this.serialRead();
                if (response && response[0] === 0xC1) {
                    configSuccess = true;
                    break;
                }
            }

            if (!configSuccess) throw new Error('Module configuration failed');

            await this.M0.write(0);
            await this.M1.write(0);
            await sleep(100);
            return true;

        } catch (err) {
            console.error('Configuration error:', err);
            return false;
        }
    }

    async send(data) {
        try {
            await this.M0.write(0);
            await this.M1.write(0);
            await sleep(100);

            const lowAddr = this.addr & 0xFF;
            const highAddr = (this.addr >> 8) & 0xFF;
            const buffer = Buffer.concat([
                Buffer.from([highAddr, lowAddr]),
                Buffer.from(data)
            ]);

            await this.serialWrite(buffer);
            await sleep(100);
            return true;
        } catch (err) {
            console.error('Send error:', err);
            return false;
        }
    }

    async receive() {
        try {
            const data = await this.serialRead();
            if (!data || data.length < 3) return null;

            const nodeAddress = (data[0] << 8) + data[1];
            const rssiValue = 256 - data[data.length - 1];
            const message = data.slice(2, -1).toString('utf-8');

            let jsonData;
            try {
                jsonData = JSON.parse(message);
            } catch {
                jsonData = message;
            }

            return {
                address: nodeAddress,
                message: jsonData,
                rssi: rssiValue,
                timestamp: new Date().toISOString()
            };
        } catch (err) {
            console.error('Receive error:', err);
            return null;
        }
    }

    async getChannelRSSI() {
        try {
            await this.M0.write(0);
            await this.M1.write(0);
            await sleep(100);

            await this.serialWrite(Buffer.from([0xC0, 0xC1, 0xC2, 0xC3, 0x00, 0x02]));
            await sleep(500);

            const response = await this.serialRead();
            if (response && response[0] === 0xC1) {
                return 256 - response[3];
            }
            return null;
        } catch (err) {
            console.error('RSSI error:', err);
            return null;
        }
    }

    // Helper methods
    serialWrite(data) {
        return new Promise((resolve, reject) => {
            this.serial.write(data, (err) => {
                if (err) reject(err);
                else resolve();
            });
        });
    }

    serialRead(timeout = 1000) {
        return new Promise((resolve) => {
            const timer = setTimeout(() => {
                this.serial.removeListener('data', handler);
                resolve(null);
            }, timeout);

            const handler = (data) => {
                clearTimeout(timer);
                resolve(data);
            };

            this.serial.once('data', handler);
        });
    }

    async cleanup() {
        try {
            await this.M0.unexport();
            await this.M1.unexport();
            await new Promise((resolve) => this.serial.close(resolve));
        } catch (err) {
            console.error('Cleanup error:', err);
        }
    }
}

module.exports = SX126x;



can you fix codebelow by using the above code

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
    console.log(Setting address to: ${address});
    myPort.write(AT+ADDRESS=${address}\r\n);
    await delay(100);  // Ensure it takes effect
}

async function setTargetAddress(targetAddress) {
    console.log(Setting target address to: ${targetAddress});
    myPort.write(AT+DEST=${targetAddress}\r\n);
    await delay(100);  // Allow time for setting to apply
}

async function setFrequency(freq) {
    console.log(Setting frequency to: ${freq});
    myPort.write(AT+FREQ=${freq}\r\n);
    await delay(100); // Wait before proceeding
}

async function sendLoRaMessage(message, targetAddress) {
    console.log(Preparing to send to ${targetAddress}: ${message});

    // Ensure target is set
    await setTargetAddress(targetAddress);

    await delay(200); // Small delay to allow setting to take effect

    console.log(Sending: ${message} to ${targetAddress});
    myPort.write(AT+SEND=${targetAddress},${Buffer.byteLength(message)},${message}\r\n);

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
    console.log([${currentTime}] Received from LoRa: ${data});

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