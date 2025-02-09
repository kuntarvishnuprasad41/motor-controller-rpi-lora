// receiver.js (Node.js)

const SerialPort = require('serialport');
const { ReadlineParser } = require('@serialport/parser-readline');
const { Buffer } = require('node:buffer');
const { Gpio } = require('onoff'); // Import onoff for GPIO

// --- Configuration ---
const serialPortPath = "/dev/ttyS0"; //  Serial port
const currentAddress = 30;       //  Receiver address
const targetAddress = 2;          //  Sender address (for replies)
const frequency = 433;           //  Frequency
const power = 22;                //  Power
const enableRssi = false;        //  RSSI reporting

// --- GPIO Setup ---
const relayOnPin = 23;  // GPIO pin for ON relay
const relayOffPin = 24; // GPIO pin for OFF relay

let relayOn, relayOff; // Declare outside the try block

try {
    // Initialize GPIO (using onoff)
    relayOn = new Gpio(relayOnPin, 'out');
    relayOff = new Gpio(relayOffPin, 'out');
    relayOn.writeSync(0); // Ensure relays are OFF initially
    relayOff.writeSync(0);
    console.log("GPIO pins initialized successfully."); // Add success message

} catch (error) {
    console.error("Error initializing GPIO:", error);
    console.error("Check GPIO permissions, pin numbers, and onoff installation.");
    // Optionally, exit the program if GPIO initialization fails:
    // process.exit(1);
}
