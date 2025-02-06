import RPi.GPIO as GPIO
import serial
import time
import datetime

class sx126x:

    # Define operating modes (constants) -  INSIDE THE CLASS
    MODE_STDBY = 0x01  # Standby mode
    MODE_TX = 0x02  # Transmit mode
    MODE_RX = 0x03  # Receive mode
    MODE_SLEEP = 0x04 # Sleep Mode

    # Raspberry Pi GPIO pins connected to M0 and M1
    M0 = 22
    M1 = 27

    # Default configuration register values (address 0x00, length 9)
    DEFAULT_CONFIG = [
        0xC2,  # Header (C2 = settings lost on power off; C0 = retained)
        0x00,  # MSB of address
        0x09,  # LSB of address
        0x00,  # Net ID (0-255)
        0x00,  # High byte of own address
        0x00,  # Low byte of own address
        0x62,  # UART baud rate (9600) + Air Data Rate (2.4k)
        0x17,  # Packet size (240 bytes) + Power (22dBm) + WOR Disable
        0x00,  # Channel (850MHz base + this value)
        0x03,  # Options:  RSSI byte + TX en
        0x00,  # MSB of encryption key
        0x00   # LSB of encryption key
    ]

    def __init__(self, serial_num, freq=433, addr=0, power=22, rssi=False):
        """Initializes the sx126x object."""

        self.serial_n = serial_num
        self.freq = freq
        self.addr = addr
        self.power = power
        self.rssi = rssi
        self.send_to = addr
        self.addr_temp = addr
        self.modem = None # Add modem to the instance variables

        # Initialize GPIO pins
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.M0, GPIO.OUT)
        GPIO.setup(self.M1, GPIO.OUT)
        self.set_mode(self.MODE_STDBY) # Start in standby mode

        # Open serial port
        try:
            self.ser = serial.Serial(serial_num, 9600)
            self.ser.flushInput()
        except serial.SerialException as e:
            print(f"Error opening serial port: {e}")
            raise  # Re-raise the exception to halt execution

        # Apply initial configuration
        self.set(freq, addr, power, rssi)

    def set_mode(self, mode):
        """Sets the operating mode by controlling M0 and M1 pins."""
        if mode == self.MODE_RX:
            GPIO.output(self.M0, GPIO.LOW)
            GPIO.output(self.M1, GPIO.LOW)
        elif mode == self.MODE_TX:
            GPIO.output(self.M0, GPIO.HIGH)
            GPIO.output(self.M1, GPIO.LOW)
        elif mode == self.MODE_STDBY:
            GPIO.output(self.M0, GPIO.LOW)
            GPIO.output(self.M1, GPIO.HIGH)
        elif mode == self.MODE_SLEEP:
            GPIO.output(self.M0, GPIO.HIGH)
            GPIO.output(self.M1, GPIO.HIGH)
        else:
            raise ValueError("Invalid mode")
        self.modem = mode # Update instance variable
        time.sleep(0.01)  # Short delay for mode change to take effect

    def write_payload(self, payload):
        """Writes a payload to the serial port."""
        self.ser.write(bytes(payload))

    def read_payload(self, length, timeout=1):
        """Reads a payload of specified length from the serial port with timeout."""
        self.ser.timeout = timeout
        data = self.ser.read(length)
        self.ser.timeout = None  # Reset timeout to default
        return data

    def set(self, freq, addr, power, rssi, air_speed=2400, net_id=0, buffer_size=240, crypt=0):
        """Configures the LoRa module parameters."""

        self.addr = addr
        self.freq = freq
        self.power = power
        self.rssi = rssi
        self.send_to = addr # Update send to address

        # Construct the configuration payload.  This is MUCH cleaner.
        config = self.DEFAULT_CONFIG[:]  # Start with default config

        config[3] = net_id & 0xFF  # Net ID
        config[4] = (addr >> 8) & 0xFF  # High byte of address
        config[5] = addr & 0xFF       # Low byte of address

        # Calculate frequency register value
        if freq >= 850:
            freq_reg = freq - 850
        elif freq >= 410:
            freq_reg = freq - 410
        else:
            raise ValueError("Invalid frequency")
        config[8] = freq_reg

        # Air data rate and UART baud rate (combined byte)
        air_speed_setting = {
            300:   0x00,
            1200:  0x01,
            2400:  0x02,
            4800:  0x03,
            9600:  0x04,
            19200: 0x05,
            38400: 0x06,
            62500: 0x07,
        }.get(air_speed, 0x02)  # Default to 2400 if invalid

        # UART is fixed at 9600 in this library
        config[6] = 0x60 | air_speed_setting

        # Buffer size and power (combined byte)
        buffer_size_setting = {
            240: 0x00,
            128: 0x40,
            64:  0x80,
            32:  0xC0,
        }.get(buffer_size, 0x00)  # Default to 240 if invalid

        power_setting = {
            22: 0x00,
            17: 0x01,
            13: 0x02,
            10: 0x03,
        }.get(power, 0x00)  # Default to 22dBm if invalid
        config[7] = buffer_size_setting | power_setting

        # Options byte: Enable RSSI byte if requested
        if rssi:
            config[9] |= 0x80 # Set bit 7
        else:
            config[9] &= ~0x80 # Clear bit 7

        # Encryption key
        config[10] = (crypt >> 8) & 0xFF  # High byte
        config[11] = crypt & 0xFF        # Low byte

        # Send configuration command (write registers)
        self.set_mode(self.MODE_STDBY) # Need to in standby to write
        self.write_payload([0xC2, 0x00, 0x09] + config[3:]) # Write from register

        # Wait for and check the response
        response = self.read_payload(3)
        if response and response[0] == 0xC1:
            # print("Configuration successful") # Debug
            pass
        else:
            print(f"Configuration failed. Response: {response.hex() if response else 'No response'}")
            

        self.set_mode(self.MODE_RX)  # Return to RX mode


    def send(self, data):
        """Sends data over LoRa."""
        if isinstance(data, str):
            data = data.encode('utf-8') # Encode string to bytes
        if not isinstance(data, bytes):
            raise TypeError("Data must be bytes or a string")

        # Construct the packet: [destination address high, low] + [data]
        packet = [(self.send_to >> 8) & 0xFF, self.send_to & 0xFF] + list(data)
        self.set_mode(self.MODE_TX)  # Switch to TX mode
        self.write_payload(packet)


    def receive(self, timeout=5):
        """Receives data over LoRa."""

        self.set_mode(self.MODE_RX)
        start_time = time.time()
        while time.time()- start_time < timeout:
            if self.ser.inWaiting() > 0:
                # First read how many bytes
                available_bytes = self.ser.inWaiting()
                r_buff = self.ser.read(available_bytes)
                #print(f"Received raw bytes: {r_buff.hex()}")

                if len(r_buff) < 2:  # At least the address
                    print("Invalid packet received (too short)")
                    return None

                # Extract sender's address
                sender_address = (r_buff[0] << 8) | r_buff[1]
                print(f"Received message from address {sender_address}")

                # Extract the data payload (everything after the address)
                payload = r_buff[2:]

                # Check if RSSI is enabled, and remove the last byte if so.
                if self.rssi:
                    if len(payload) > 0:
                        rssi_value = - (256 - payload[-1])  # Convert to signed dBm
                        print(f"RSSI: {rssi_value} dBm")
                        payload = payload[:-1]  # Remove RSSI byte from payload
                    else:
                        print("Warning: RSSI enabled, but no RSSI byte received.")

                print(f"Message: {payload.decode('utf-8', 'ignore')}") # Decode
                return payload
            time.sleep(0.1) # Short sleep to prevent busy loop
        return None


    def cancel_receive(self):
        """Cancels any ongoing receive operation.  Essential for power loss."""
        # Put module on Standby mode
        self.set_mode(self.MODE_STDBY)