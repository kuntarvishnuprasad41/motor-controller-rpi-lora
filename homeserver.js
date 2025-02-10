const SX126X = require('./sx126x'); // Assuming you saved the converted class in sx126x.js
const readline = require('readline');

let oldSettings; // No direct equivalent to termios in Node.js for raw mode in this simple example

async function main() {
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout
    });

    console.log("Enter curr node address (0-65535):");
    let current_address = 0;
    while (!current_address) {
        const addressInput = await new Promise(resolve => rl.question('', resolve));
        try {
            current_address = parseInt(addressInput);
            if (isNaN(current_address) || current_address < 0 || current_address > 65535) {
                console.log("Invalid input. Please enter a number between 0 and 65535:");
                current_address = undefined; // Reset to loop again
            }
        } catch (e) {
            console.log("Invalid input. Please enter a number between 0 and 65535:");
        }
    }


    // const node = new SX126X("/dev/ttyS0", 433, current_address, 22, false); // Replace "/dev/ttyS0" if needed
    // const node = new SX126X(null, 433, current_address, 22, false); // Pass null for serial_num in constructor
    // node.beginSerial("/dev/ttyS0"); // Initialize serial port AFTER getting current_address
    const node = new SX126X(null, 433, current_address, 22, false); // Pass null for serial_num in constructor (not used anymore)
    node.beginSerial("/dev/ttyS0"); // Initialize serial port
    node.set(433, current_address, 22, false); // Call set AFTER serial port is initialized



    function send_command(command, target_address) {
        const timestamp = new Date().toISOString().replace(/T/, ' ').replace(/\..+/, ''); // "YYYY-MM-DD HH:MM:SS" format
        const message = { command: command, time: timestamp };
        const json_message = JSON.stringify(message);

        const original_address = node.addr;
        node.addr_temp = node.addr;
        node.set(node.freq, target_address, node.power, node.rssi)
            .then(() => {
                node.send(json_message);
                return new Promise(resolve => setTimeout(resolve, 200)); // time.sleep(0.2) as a Promise
            })
            .then(() => {
                return node.set(node.freq, original_address, node.power, node.rssi);
            })
            .then(() => {
                console.log(`Command sent to ${target_address}.`);
            })
            .catch(error => {
                console.error("Error in send_command:", error); // Handle errors in promise chain
            });
    }


    console.log("Enter target node address (0-65535):");
    let target_address = 30;
    while (!target_address) {
        const addressInput = await new Promise(resolve => rl.question('', resolve));
        try {
            target_address = parseInt(addressInput);
            if (isNaN(target_address) || target_address < 0 || target_address > 65535) {
                console.log("Invalid input. Please enter a number between 0 and 65535:");
                target_address = undefined; // Reset to loop again
            }
        } catch (e) {
            console.log("Invalid input. Please enter a number between 0 and 65535.");
        }
    }

    console.log("Press \x1b[1;32m1\x1b[0m to send Motor ON command");
    console.log("Press \x1b[1;32m2\x1b[0m to send Motor OFF command");
    console.log("Press \x1b[1;32m3\x1b[0m to send Motor STATUS request");
    console.log("Press Esc to exit (not directly supported in readline, use Ctrl+C to exit)");


    const stdin = process.stdin;
    stdin.setRawMode(true); // attempt to set raw mode - might behave differently from python tty.setcbreak
    stdin.resume();
    stdin.setEncoding('utf8');


    stdin.on('data', async function (key) {
        // Check for incoming data first - Placeholder as receive() needs to be implemented in SX126X class
        const received_data = await node.receive(); // Assuming you will implement receive() in SX126X class
        if (received_data) {
            const current_time = new Date().toISOString().replace(/T/, ' ').replace(/\..+/, '');
            console.log(`[${current_time}] Received: ${received_data}`);
        }


        if (key === '\x1b') { // ESC key
            console.log('Exiting...');
            rl.close();
            process.exit();
        }

        if (key === '1') {
            send_command("ON", target_address);
        } else if (key === '2') {
            send_command("OFF", target_address);
        } else if (key === '3') {
            send_command("STATUS", target_address);
        }

        // Small delay - not strictly needed with event-driven Node.js but for similar behavior
        await new Promise(resolve => setTimeout(resolve, 10)); // time.sleep(0.01) equivalent
    });


    console.log("Listening for commands and messages... (Press Ctrl+C or Esc to exit)");


}

main().catch(error => {
    console.error("Unhandled error:", error);
    process.exit(1);
});