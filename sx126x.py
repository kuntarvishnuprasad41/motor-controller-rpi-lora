import RPi.GPIO as GPIO
import serial
import time
import datetime

class sx126x:

    # Define operating modes (constants)
    MODE_STDBY = 0x01
    MODE_TX = 0x02
    MODE_RX = 0x03
    MODE_SLEEP = 0x04

    # Raspberry Pi GPIO pins connected to M0 and M1
    M0 = 22
    M1 = 27

    # Default configuration register values
    DEFAULT_CONFIG = [
        0xC2,  # Header
        0x00,  # MSB of address (Placeholder)
        0x09,  # LSB of address (Placeholder)
        0x00,  # Net ID
        0x00,  # High byte of own address
        0x00,  # Low byte of own address
        0x62,  # UART baud rate (9600) + Air Data Rate (2.4k)
        0x17,  # Packet size (240 bytes) + Power (22dBm) + WOR Disable
        0x00,  # Channel
        0x03,  # Options: RSSI byte + TX en
        0x00,  # MSB of encryption key
        0x00   # LSB of encryption key
    ]

    def __init__(self, serial_num, freq=433, addr=0, power=22, rssi=False):
        self.serial_n = serial_num
        self.freq = freq
        self.addr = addr  # This is now the *own* address of THIS module
        self.power = power
        self.rssi = rssi
        self.modem = None

        # Initialize GPIO pins
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.M0, GPIO.OUT)
        GPIO.setup(self.M1, GPIO.OUT)
        self.set_mode(self.MODE_STDBY)

        # Open serial port
        try:
            self.ser = serial.Serial(serial_num, 9600)
            self.ser.flushInput()
        except serial.SerialException as e:
            print(f"Error opening serial port: {e}")
            raise

        # Apply initial configuration
        self.set(freq, addr, power, rssi)

    def set_mode(self, mode):
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
        self.modem = mode
        time.sleep(0.01)

    def write_payload(self, payload):
        self.ser.write(bytes(payload))

    def read_payload(self, length, timeout=1):
        self.ser.timeout = timeout
        data = self.ser.read(length)
        self.ser.timeout = None
        return data

    def set(self, freq, addr, power, rssi, air_speed=2400, net_id=0, buffer_size=240, crypt=0):
        self.addr = addr  # Store the *own* address

        config = self.DEFAULT_CONFIG[:]
        config[3] = net_id & 0xFF
        config[4] = (addr >> 8) & 0xFF  # High byte of *own* address
        config[5] = addr & 0xFF       # Low byte of *own* address

        if freq >= 850:
            freq_reg = freq - 850
        elif freq >= 410:
            freq_reg = freq - 410
        else:
            raise ValueError("Invalid frequency")
        config[8] = freq_reg

        air_speed_setting = {
            300:   0x00,
            1200:  0x01,
            2400:  0x02,
            4800:  0x03,
            9600:  0x04,
            19200: 0x05,
            38400: 0x06,
            62500: 0x07,
        }.get(air_speed, 0x02)
        config[6] = 0x60 | air_speed_setting

        buffer_size_setting = {
            240: 0x00,
            128: 0x40,
            64:  0x80,
            32:  0xC0,
        }.get(buffer_size, 0x00)
        power_setting = {
            22: 0x00,
            17: 0x01,
            13: 0x02,
            10: 0x03,
        }.get(power, 0x00)
        config[7] = buffer_size_setting | power_setting

        if rssi:
            config[9] |= 0x80
        else:
            config[9] &= ~0x80

        config[10] = (crypt >> 8) & 0xFF
        config[11] = crypt & 0xFF

        self.set_mode(self.MODE_STDBY)
        self.write_payload([0xC2, 0x00, 0x09] + config[3:])

        response = self.read_payload(3)
        if not (response and response[0] == 0xC1):
            print(f"Configuration failed. Response: {response.hex() if response else 'No response'}")
        self.set_mode(self.MODE_RX)

    def send(self, destination_address, data):
        """Sends data to the specified destination address."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        if not isinstance(data, bytes):
            raise TypeError("Data must be bytes or a string")

        # Construct the packet: [destination address high, low] + [data]
        packet = [(destination_address >> 8) & 0xFF, destination_address & 0xFF] + list(data)
        print(f"Sending packet: {bytes(packet).hex()}")  # Debug: Show the packet
        self.set_mode(self.MODE_TX)
        self.write_payload(packet)
        time.sleep(0.1) # Added a small delay

    def receive(self, timeout=5):
        """Receives data with improved address handling and serial reading."""
        self.set_mode(self.MODE_RX)
        start_time = time.time()
        received_data = bytearray() # Use bytearray

        while time.time() - start_time < timeout:
            if self.ser.inWaiting() > 0:
                received_data += self.ser.read(self.ser.inWaiting())  # Read all available
                print(f"Received raw bytes: {received_data.hex()}") # Debug
                # Check if we have enough bytes for the address
                if len(received_data) >= 2:
                    sender_address = (received_data[0] << 8) | received_data[1]
                    print(f"Received message from address {sender_address}")

                    # Check if this message is for us (or broadcast)
                    if sender_address == self.addr or sender_address == 65535:
                        payload = received_data[2:]  # Data starts after address

                        if self.rssi and len(payload) > 0:
                            rssi_value = -(256 - payload[-1])
                            print(f"RSSI: {rssi_value} dBm")
                            payload = payload[:-1]  # Remove RSSI byte

                        print(f"Message: {payload.decode('utf-8', 'ignore')}")
                        return payload
                    else: # Message is not for us
                        received_data = bytearray() #Clear buffer
                        return None # Return None if not for us.

            time.sleep(0.01)  # Shorter sleep for responsiveness

        return None  # Timeout
    def cancel_receive(self):
        self.set_mode(self.MODE_STDBY)