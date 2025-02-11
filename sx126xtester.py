import RPi.GPIO as GPIO
import serial
import time

class sx126x:
    M0 = 22  # GPIO pin for M0
    M1 = 27  # GPIO pin for M1

    cfg_reg = [0xC2, 0x00, 0x09, 0x00, 0x00, 0x00, 0x62, 0x00, 0x17, 0x00, 0x00, 0x00]

    def __init__(self, serial_num, freq, addr, power, rssi):
        self.rssi = rssi
        self.addr = addr
        self.freq = freq
        self.serial_n = serial_num
        self.power = power
        self.send_to = addr

        # Setup GPIO for M0 and M1
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.M0, GPIO.OUT)
        GPIO.setup(self.M1, GPIO.OUT)
        GPIO.output(self.M0, GPIO.LOW)
        GPIO.output(self.M1, GPIO.HIGH)

        # Debug Print
        print(f"Initializing LoRa module on {serial_num} at 9600 baud...")
        
        try:
            self.ser = serial.Serial(serial_num, 9600, timeout=1)
            self.ser.flushInput()
            print("Serial connection established successfully!")
        except Exception as e:
            print(f"Error opening serial: {e}")
            return

        # Configure LoRa module
        self.set(freq, addr, power, rssi)

    def set(self, freq, addr, power, rssi, air_speed=2400):
        self.send_to = addr
        self.addr = addr

        # Set GPIO for configuration mode
        GPIO.output(self.M0, GPIO.LOW)
        GPIO.output(self.M1, GPIO.HIGH)
        time.sleep(0.1)

        # Compute frequency
        if freq > 850:
            freq_temp = freq - 850
        elif freq > 410:
            freq_temp = freq - 410
        else:
            print("Invalid frequency range")
            return

        power_temp = self.power_cal(power)

        if rssi:
            rssi_temp = 0x80  # Enable RSSI
        else:
            rssi_temp = 0x00

        # Set configuration registers
        self.cfg_reg[3] = addr >> 8 & 0xff
        self.cfg_reg[4] = addr & 0xff
        self.cfg_reg[6] = 0x60  # Default UART baud rate 9600
        self.cfg_reg[7] = power_temp + freq_temp
        self.cfg_reg[9] = rssi_temp

        # Send configuration to LoRa module
        try:
            self.ser.write(bytes(self.cfg_reg))
            time.sleep(0.5)
            print("LoRa configuration updated successfully!")
        except Exception as e:
            print(f"Error sending config: {e}")

    def send(self, target_addr, message):
        if not self.ser:
            print("Serial connection not established!")
            return False

        message_bytes = message.encode('utf-8')
        packet = bytes([target_addr >> 8 & 0xff, target_addr & 0xff]) + message_bytes

        try:
            self.ser.write(packet)
            print(f"Message sent to {target_addr}: {message}")
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False

    def receive(self):
        if not self.ser:
            print("Serial connection not established!")
            return None

        try:
            if self.ser.in_waiting > 0:
                received_data = self.ser.read(self.ser.in_waiting)
                print(f"Received: {received_data.decode('utf-8', errors='ignore')}")
                return received_data
        except Exception as e:
            print(f"Error receiving data: {e}")
            return None

    def power_cal(self, power):
        if power == 22:
            return 0x00
        elif power == 17:
            return 0x01
        elif power == 13:
            return 0x02
        elif power == 10:
            return 0x03
        else:
            print("Invalid power setting")
            return 0x00

    def close(self):
        print("Closing serial connection and cleaning up GPIO...")
        if self.ser:
            self.ser.close()
        GPIO.cleanup()
