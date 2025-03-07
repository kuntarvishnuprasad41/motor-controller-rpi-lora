// receiver.js (Node.js)

const SerialPort = require('serialport');
const { ReadlineParser } = require('@serialport/parser-readline');
const { Buffer } = require('node:buffer');

// --- Configuration ---
const serialPortPath = "/dev/ttyS0"; //  Serial port
const currentAddress = 30;       //  Receiver address
const targetAddress = 2;          //  Sender address (for replies)
const frequency = 433;           //  Frequency
const power = 22;                //  Power
const enableRssi = false;        //  RSSI reporting

// --- Helper Functions ---
function setGpioOutput(pin) {
    try {
        execSync(`pinctrl ${pin} op`);
        console.log(`GPIO ${pin} set to output`);
    } catch (error) {
        console.error(`Error setting GPIO ${pin} to output:`, error.message);
    }
}

function setGpioHigh(pin) {
    try {
        execSync(`pinctrl ${pin} dh`);
        console.log(`GPIO ${pin} set to HIGH`);
    } catch (error) {
        console.error(`Error setting GPIO ${pin} HIGH:`, error.message);
    }
}

function setGpioLow(pin) {
    try {
        execSync(`pinctrl ${pin} dl`);
        console.log(`GPIO ${pin} set to LOW`);
    } catch (error) {
        console.error(`Error setting GPIO ${pin} LOW:`, error.message);
    }
}
// --- sx126x Class ---
class sx126x {
    constructor(serial_num, freq, addr, power, rssi) {
        this.M0 = 22;
        this.M1 = 27;
        this.cfg_reg = [0xC2, 0x00, 0x09, 0x00, 0x00, 0x00, 0x62, 0x00, 0x17, 0x00, 0x00, 0x00];
        this.get_reg = Buffer.alloc(12);
        this.rssi = rssi;
        this.addr = addr;
        this.freq = freq;
        this.serial_n = serial_num;
        this.power = power;
        this.send_to = addr;
        this.addr_temp = 0;
        this.air_speed = 2400;

        this.SX126X_UART_BAUDRATE_1200 = 0x00;
        this.SX126X_UART_BAUDRATE_2400 = 0x20;
        this.SX126X_UART_BAUDRATE_4800 = 0x40;
        this.SX126X_UART_BAUDRATE_9600 = 0x60;
        this.SX126X_UART_BAUDRATE_19200 = 0x80;
        this.SX126X_UART_BAUDRATE_38400 = 0xA0;
        this.SX126X_UART_BAUDRATE_57600 = 0xC0;
        this.SX126X_UART_BAUDRATE_115200 = 0xE0;

        this.SX126X_AIR_SPEED_300bps = 0x00;
        this.SX126X_AIR_SPEED_1200bps = 0x01;
        this.SX126X_AIR_SPEED_2400bps = 0x02;
        this.SX126X_AIR_SPEED_4800bps = 0x03;
        this.SX126X_AIR_SPEED_9600bps = 0x04;
        this.SX126X_AIR_SPEED_19200bps = 0x05;
        this.SX126X_AIR_SPEED_38400bps = 0x06;
        this.SX126X_AIR_SPEED_62500bps = 0x07;

        this.SX126X_PACKAGE_SIZE_240_BYTE = 0x00;
        this.SX126X_PACKAGE_SIZE_128_BYTE = 0x40;
        this.SX126X_PACKAGE_SIZE_64_BYTE = 0x80;
        this.SX126X_PACKAGE_SIZE_32_BYTE = 0xC0;

        this.SX126X_Power_22dBm = 0x00;
        this.SX126X_Power_17dBm = 0x01;
        this.SX126X_Power_13dBm = 0x02;
        this.SX126X_Power_10dBm = 0x03;

        // Setup serial port
        this.port = new SerialPort.SerialPort({
            path: serial_num,
            baudRate: 9600,
            dataBits: 8,
            stopBits: 1,
            parity: 'none',
        });

        this.parser = this.port.pipe(new ReadlineParser({ delimiter: '\r\n' }));
        this.set(freq, addr, power, rssi);

        this.port.on('error', function (err) {
            console.error('SerialPort Error: ', err.message);
        });

        // Initialize GPIO pins as outputs (using pinctrl)
        setGpioOutput(this.M0); // Assuming M0 and M1 are GPIO numbers
        setGpioOutput(this.M1);
    }

    set(freq, addr, power, rssi, air_speed = 2400, net_id = 0, buffer_size = 240, crypt = 0, relay = false, lbt = false, wor = false) {
        this.send_to = addr;
        this.addr = addr;
        // We should pull up the M1 pin when sets the module
        setGpioLow(this.M0); // Assuming M0 and M1 are GPIO numbers
        setGpioHigh(this.M1);

        setTimeout(() => {
            let low_addr = addr & 0xff;
            let high_addr = addr >> 8 & 0xff;
            let net_id_temp = net_id & 0xff;
            let freq_temp;
            if (freq > 850) {
                freq_temp = freq - 850;
            } else if (freq > 410) {
                freq_temp = freq - 410;
            }

            let air_speed_temp = this.air_speed_cal(air_speed);
            let buffer_size_temp = this.buffer_size_cal(buffer_size);
            let power_temp = this.power_cal(power);
            let rssi_temp = rssi ? 0x80 : 0x00;
            let l_crypt = crypt & 0xff;
            let h_crypt = crypt >> 8 & 0xff;

            this.cfg_reg[3] = high_addr;
            this.cfg_reg[4] = low_addr;
            this.cfg_reg[5] = net_id_temp;
            this.cfg_reg[6] = this.SX126X_UART_BAUDRATE_9600 + air_speed_temp;
            this.cfg_reg[7] = buffer_size_temp + power_temp + 0x20;
            this.cfg_reg[8] = freq_temp;
            this.cfg_reg[9] = 0x03 + rssi_temp;
            this.cfg_reg[10] = h_crypt;
            this.cfg_reg[11] = l_crypt;

            for (let i = 0; i < 2; i++) {
                this.port.write(Buffer.from(this.cfg_reg));
            }
            setGpioLow(this.M0); // Assuming M0 and M1 are GPIO numbers
            setGpioLow(this.M1);
        }, 100); // Delay for GPIO setting
    }

    air_speed_cal(airSpeed) {
        const air_speed_c = {
            1200: this.SX126X_AIR_SPEED_1200bps,
            2400: this.SX126X_AIR_SPEED_2400bps,
            4800: this.SX126X_AIR_SPEED_4800bps,
            9600: this.SX126X_AIR_SPEED_9600bps,
            19200: this.SX126X_AIR_SPEED_19200bps,
            38400: this.SX126X_AIR_SPEED_38400bps,
            62500: this.SX126X_AIR_SPEED_62500bps
        };
        return air_speed_c[airSpeed] !== undefined ? air_speed_c[airSpeed] : null;
    }

    power_cal(power) {
        const power_c = {
            22: this.SX126X_Power_22dBm,
            17: this.SX126X_Power_17dBm,
            13: this.SX126X_Power_13dBm,
            10: this.SX126X_Power_10dBm
        };
        return power_c[power] !== undefined ? power_c[power] : null;
    }

    buffer_size_cal(bufferSize) {
        const buffer_size_c = {
            240: this.SX126X_PACKAGE_SIZE_240_BYTE,
            128: this.SX126X_PACKAGE_SIZE_128_BYTE,
            64: this.SX126X_PACKAGE_SIZE_64_BYTE,
            32: this.SX126X_PACKAGE_SIZE_32_BYTE
        };
        return buffer_size_c[bufferSize] !== undefined ? power_c[power] : null;
    }

    get_settings() {
        // NOT FULLY IMPLEMENTED
    }

    send(data) {
        this.M1_gpio.writeSync(0);
        this.M0_gpio.writeSync(0);
        setTimeout(() => {
            let l_addr = this.addr_temp & 0xff;
            let h_addr = this.addr_temp >> 8 & 0xff;
            const buffer = Buffer.from([h_addr, l_addr, ...data]);
            this.port.write(buffer);
        }, 100);
    }

    receive(callback) {
        this.parser.on('data', (data) => {
            console.log("Raw data from serial:", data);

            try {
                const buffer = Buffer.from(data)
                if (buffer.length < 3) {
                    console.log("Incomplete packet");
                    return;
                }
                const node_address = (buffer[0] << 8) + buffer[1];
                const rssi = 256 - buffer[buffer.length - 1];
                const message_bytes = buffer.slice(2, -1);
                const message_str = message_bytes.toString('utf-8');
                let json_message;
                const start = message_str.indexOf('{');
                const end = message_str.lastIndexOf('}') + 1;

                if (start !== -1 && end !== -1) {
                    json_message = message_str.substring(start, end);
                    console.log(json_message)
                    const time = new Date().toISOString();
                    callback({ time, message: json_message, rssi, node_address }); // Pass to callback

                }
                else {
                    console.log("No JSON found in message");
                    console.log(message_str)
                }
            }
            catch (error) {
                console.error("Error processing received data:", error);
            }
        });
    }

    get_channel_rssi() {
        // NOT FULLY IMPLEMENTED
    }
}

// --- Main Program Logic ---
setGpioOutput(relayOnPin);
setGpioOutput(relayOffPin);

const node = new sx126x(serialPortPath, frequency, currentAddress, power, enableRssi);
function sendReply(message, targetAddress) {
    const timestamp = new Date().toISOString();
    const replyMessage = { reply: message, time: timestamp };
    const jsonMessage = JSON.stringify(replyMessage);

    const originalAddress = node.addr;
    node.addr_temp = node.addr;
    node.set(node.freq, targetAddress, node.power, node.rssi);
    node.send(Buffer.from(jsonMessage, 'utf8'));
    node.set(node.freq, originalAddress, node.power, node.rssi);
    console.log(`Reply sent to ${targetAddress}: ${message}`);
}

// Replace the original receive method to use a callback:
node.receive((receivedData) => {
    try {
        const receivedJson = JSON.parse(receivedData.message);
        if (receivedJson.command) {
            const command = receivedJson.command;
            const currentTime = new Date().toISOString();
            console.log(`[${currentTime}] Received command: ${command}`);

            if (command === "ON") {
                setGpioLow(relayOffPin);  // Ensure only one relay is on
                setGpioHigh(relayOnPin);   // Turn ON relay
                sendReply("Motor on", targetAddress);
            } else if (command === "OFF") {
                setGpioLow(relayOnPin);   // Turn OFF relay
                setGpioHigh(relayOffPin);
                setTimeout(() => {
                    setGpioLow(relayOffPin);
                }, 500);
                sendReply("Motor off", targetAddress);
            } else if (command === "STATUS") {
                // There's no direct way to read the GPIO state with pinctrl
                // This is just a placeholder - you might need to use a different method
                // to get the actual status
                sendReply("Cannot read motor status with pinctrl", targetAddress);
            } else {
                sendReply("Unknown command", targetAddress);
            }
        }
    } catch (error) {
        console.error("Error processing command:", error);
    }
});

// --- Signal Handling (for graceful shutdown) ---
process.on('SIGINT', () => {
    console.log("Shutting down...");
    setGpioLow(relayOnPin);   // Turn OFF relays
    setGpioLow(relayOffPin);
    process.exit(0);
});

process.on('uncaughtException', (err) => {
    console.error('Uncaught Exception:', err);
    setGpioLow(relayOnPin);   // Turn OFF relays on error
    setGpioLow(relayOffPin);
    process.exit(1);
});

console.log("Receiver running. Waiting for commands...");
