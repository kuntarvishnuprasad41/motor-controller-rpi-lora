// sender.js (Node.js)

const SerialPort = require('serialport');
const { Buffer } = require('node:buffer');

// --- Configuration ---
const serialPortPath = "/dev/ttyS0"; // Serial port
const currentAddress = 2;           // Sender address
const targetAddress = 30;            // Receiver address
const frequency = 433;            // Frequency
const power = 22;                 // Power
const enableRssi = false;         // RSSI reporting

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

        this.port.on('error', function (err) {
            console.error('SerialPort Error: ', err.message);
        });

        this.set(freq, addr, power, rssi);
    }

    set(freq, addr, power, rssi, air_speed = 2400, net_id = 0, buffer_size = 240, crypt = 0, relay = false, lbt = false, wor = false) {
        this.send_to = addr;
        this.addr = addr;

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
        }, 100);
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

    send(data) {
        let l_addr = this.addr_temp & 0xff;
        let h_addr = this.addr_temp >> 8 & 0xff;
        const buffer = Buffer.from([h_addr, l_addr, ...data]);
        this.port.write(buffer);
    }
}

// --- Main Program Logic ---
const node = new sx126x(serialPortPath, frequency, currentAddress, power, enableRssi);

// Function to send a message
function sendMessage(command) {
    const timestamp = new Date().toISOString();
    const message = {
        command: command,
        timestamp: timestamp
    };
    const messageString = JSON.stringify(message);

    node.addr_temp = targetAddress; // Set the target address
    node.send(Buffer.from(messageString, 'utf8'));
    console.log(`Sent: ${messageString}`);
}

// Cycle through commands every 5 seconds
let commandIndex = 0;
const commands = ["ON", "OFF", "STATUS"];

setInterval(() => {
    const command = commands[commandIndex];
    sendMessage(command);
    commandIndex = (commandIndex + 1) % commands.length;
}, 5000);
