# This file is used for LoRa and Raspberry Pi4B/Pi Zero
# This is the main class file that is often used for LoRa parameters settings

import RPi.GPIO as GPIO
import serial
import time
import datetime
import json


class sx126x:

    M0 = 22
    M1 = 27
    # if the header is 0xC0, then the LoRa register settings dont lost when it poweroff, and 0xC2 will be lost.
    # cfg_reg = [0xC0,0x00,0x09,0x00,0x00,0x00,0x62,0x00,0x17,0x00,0x00,0x00]
    cfg_reg = [0xC2,0x00,0x09,0x00,0x00,0x00,0x62,0x00,0x17,0x00,0x00,0x00]
    get_reg = bytes(12)
    rssi = False
    addr = 65535
    serial_n = ""
    send_to = 0
    addr_temp = 0
    freq = 868
    power = 22
    air_speed =2400

    SX126X_UART_BAUDRATE_1200 = 0x00
    SX126X_UART_BAUDRATE_2400 = 0x20
    SX126X_UART_BAUDRATE_4800 = 0x40
    SX126X_UART_BAUDRATE_9600 = 0x60
    SX126X_UART_BAUDRATE_19200 = 0x80
    SX126X_UART_BAUDRATE_38400 = 0xA0
    SX126X_UART_BAUDRATE_57600 = 0xC0
    SX126X_UART_BAUDRATE_115200 = 0xE0

    SX126X_AIR_SPEED_300bps = 0x00
    SX126X_AIR_SPEED_1200bps = 0x01
    SX126X_AIR_SPEED_2400bps = 0x02
    SX126X_AIR_SPEED_4800bps = 0x03
    SX126X_AIR_SPEED_9600bps = 0x04
    SX126X_AIR_SPEED_19200bps = 0x05
    SX126X_AIR_SPEED_38400bps = 0x06
    SX126X_AIR_SPEED_62500bps = 0x07

    SX126X_PACKAGE_SIZE_240_BYTE = 0x00
    SX126X_PACKAGE_SIZE_128_BYTE = 0x40
    SX126X_PACKAGE_SIZE_64_BYTE = 0x80
    SX126X_PACKAGE_SIZE_32_BYTE = 0xC0

    SX126X_Power_22dBm = 0x00
    SX126X_Power_17dBm = 0x01
    SX126X_Power_13dBm = 0x02
    SX126X_Power_10dBm = 0x03

    def __init__(self,serial_num,freq,addr,power,rssi):
        self.rssi = rssi
        self.addr = addr
        self.freq = freq
        self.serial_n = serial_num
        self.power = power
        self.send_to = addr

        # Initial the GPIO for M0 and M1 Pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.M0,GPIO.OUT)
        GPIO.setup(self.M1,GPIO.OUT)
        GPIO.output(self.M0,GPIO.LOW)
        GPIO.output(self.M1,GPIO.HIGH)

        # The hardware UART of Pi3B+,Pi4B is /dev/ttyS0
        self.ser = serial.Serial(serial_num,9600)
        self.ser.flushInput()
        self.set(freq,addr,power,rssi)

    def set(self,freq,addr,power,rssi,air_speed=2400,\
            net_id=0,buffer_size = 240,crypt=0,\
            relay=False,lbt=False,wor=False):
        self.send_to = addr
        self.addr = addr
        # We should pull up the M1 pin when sets the module
        GPIO.output(self.M0,GPIO.LOW)
        GPIO.output(self.M1,GPIO.HIGH)
        time.sleep(0.1)
        low_addr = addr & 0xff
        high_addr = addr >> 8 & 0xff
        net_id_temp = net_id & 0xff
        if freq > 850:
            freq_temp = freq - 850
        elif freq >410:
            freq_temp = freq - 410

        air_speed_temp = self.air_speed_cal(air_speed)
        # if air_speed_temp != None:

        buffer_size_temp = self.buffer_size_cal(buffer_size)
        # if air_speed_temp != None:

        power_temp = self.power_cal(power)
        #if power_temp != None:

        # At this moment there is a bug in get_channel_rssi() function with SX1268 HAT
        # The get_channel_rssi() function works well in SX1262 HAT
        # To solve the problem for SX1268, we use an alternative method to obtain RSSI value
        # We enable the seventh bit of 06H register
        # and obatin the RSSI value when the packet is received.

        if rssi:
            # if use get_channel_rssi() func,  then uncomment next line and comment next to next line!
            # rssi_temp = 0x20
            rssi_temp = 0x80
        else:
            rssi_temp = 0x00

        l_crypt = crypt & 0xff
        h_crypt = crypt >> 8 & 0xff

        self.cfg_reg[3] = high_addr
        self.cfg_reg[4] = low_addr
        self.cfg_reg[5] = net_id_temp
        self.cfg_reg[6] = self.SX126X_UART_BAUDRATE_9600 + air_speed_temp
        #
        # it will enable to read noise rssi value when add 0x20 as follow
        #
        self.cfg_reg[7] = buffer_size_temp + power_temp + 0x20
        self.cfg_reg[8] = freq_temp
        #
        # it will output a packet rssi value following received message
        # when enable seventh bit with 06H register(rssi_temp = 0x80)
        #
        self.cfg_reg[9] = 0x03 + rssi_temp
        self.cfg_reg[10] = h_crypt
        self.cfg_reg[11] = l_crypt
        self.ser.flushInput()

        for i in range(2):
            self.ser.write(bytes(self.cfg_reg))
            r_buff = 0
            time.sleep(0.2)
            if self.ser.inWaiting() > 0:
                time.sleep(0.1)
                r_buff = self.ser.read(self.ser.inWaiting())
                if r_buff[0] == 0xC1:
                    pass
                    # print("parameters setting is :",end='')
                    # for i in self.cfg_reg:
                        # print(hex(i),end=' ')

                    # print('\r\n')
                    # print("parameters return is  :",end='')
                    # for i in r_buff:
                        # print(hex(i),end=' ')
                    # print('\r\n')
                else:
                    pass
                    #print("parameters setting fail :",r_buff)
                break
            else:
                print("trying again!")
                self.ser.flushInput()
                time.sleep(0.2)
                print('\x1b[1A',end='\r')
                if i == 1:
                    print("setting fail, press Esc to exit and run again")
                    time.sleep(2)
                    print('\x1b[1A',end='\r')
                pass

        GPIO.output(self.M0,GPIO.LOW)
        GPIO.output(self.M1,GPIO.LOW)
        time.sleep(0.1)

    def air_speed_cal(self,airSpeed):
        air_speed_c = {
            1200:self.SX126X_AIR_SPEED_1200bps,
            2400:self.SX126X_AIR_SPEED_2400bps,
            4800:self.SX126X_AIR_SPEED_4800bps,
            9600:self.SX126X_AIR_SPEED_9600bps,
            19200:self.SX126X_AIR_SPEED_19200bps,
            38400:self.SX126X_AIR_SPEED_38400bps,
            62500:self.SX126X_AIR_SPEED_62500bps
        }
        return air_speed_c.get(airSpeed,None)

    def power_cal(self,power):
        power_c = {
            22:self.SX126X_Power_22dBm,
            17:self.SX126X_Power_17dBm,
            13:self.SX126X_Power_13dBm,
            10:self.SX126X_Power_10dBm
        }
        return power_c.get(power,None)

    def buffer_size_cal(self,bufferSize):
        buffer_size_c = {
            240:self.SX126X_PACKAGE_SIZE_240_BYTE,
            128:self.SX126X_PACKAGE_SIZE_128_BYTE,
            64:self.SX126X_PACKAGE_SIZE_64_BYTE,
            32:self.SX126X_PACKAGE_SIZE_32_BYTE
        }
        return buffer_size_c.get(bufferSize,None)

    def get_settings(self):
        # the pin M1 of lora HAT must be high when enter setting mode and get parameters
        GPIO.output(self.M1,GPIO.HIGH)
        time.sleep(0.1)

        # send command to get setting parameters
        self.ser.write(bytes([0xC1,0x00,0x09]))
        if self.ser.inWaiting() > 0:
            time.sleep(0.1)
            self.get_reg = self.ser.read(self.ser.inWaiting())

        # check the return characters from HAT and print the setting parameters
        if self.get_reg[0] == 0xC1 and self.get_reg[2] == 0x09:
            fre_temp = self.get_reg[8]
            addr_temp = self.get_reg[3] + self.get_reg[4]
            air_speed_temp = self.get_reg[6] & 0x03
            power_temp = self.get_reg[7] & 0x03

            air_speed_dic = {
                0x00:"300bps",
                0x01:"1200bps",
                0x02:"2400bps",
                0x03:"4800bps",
                0x04:"9600bps",
                0x05:"19200bps",
                0x06:"38400bps",
                0x07:"62500bps"
            }
            power_dic ={
                0x00:"22dBm",
                0x01:"17dBm",
                0x02:"13dBm",
                0x03:"10dBm"
            }

            print("Frequence is {0}.125MHz.",fre_temp)
            print("Node address is {0}.",addr_temp)
            print("Air speed is "+ air_speed_dic(air_speed_temp))
            print("Power is " + power_dic(power_temp))
            GPIO.output(self.M1,GPIO.LOW)

    def send(self,data):
        GPIO.output(self.M1,GPIO.LOW)
        GPIO.output(self.M0,GPIO.LOW)
        time.sleep(0.1)

        # add the node address ,and the node of address is 65535 can able to find who sends message
        l_addr = self.addr_temp & 0xff
        h_addr = self.addr_temp >> 8 & 0xff

        self.ser.write(bytes([h_addr,l_addr])+data.encode())
        # if self.rssi == True:
            # self.get_channel_rssi()
        time.sleep(0.1)

    def receive(self):
        if self.ser.inWaiting() > 0:
            time.sleep(0.5)
            r_buff = self.ser.read(self.ser.inWaiting())

            node_address = (r_buff[0] << 8) + r_buff[1]
            print(f"receive message from address \033[1;32m{node_address} node\033[0m {r_buff[2:]}")

            try:
                message_str = r_buff.decode('utf-8')
            except UnicodeDecodeError as e:
                print(f"Error decoding message: {e}")
                print(f"Raw data: {r_buff}")
                return None  # Return None to indicate an error

            try:
                start = message_str.find('{')  # Find the first opening curly brace
                end = message_str.rfind('}') + 1 # Find the last closing curly brace
                if start != -1 and end != -1:
                    json_message = message_str[start:end]
                else:
                    print("Message format error, no JSON found")
                    print("Raw data: " + message_str)
                    return message_str # Return None to indicate an error

            except Exception as e:
                print(f"Error extracting JSON: {e}")
                print("Raw data: " + message_str)
                return None # Return None to indicate an error

            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            print(f"@ [{current_time}] ")
            rssi = 256 - r_buff[-1:][0]
            print(f"the packet rssi value: -{rssi}dBm")
            self.get_channel_rssi()
            e = datetime.datetime.now()
            with open("g.txt", "a") as f:
                f.write(f"Packet RSSI: -{rssi}dBm Current date and time = {e}\n")
            print(f"@ [{rssi}]dBm ")

            

            if self.rssi:
                    rssi = 256 - r_buff[-1:][0]
                    print(f"the packet rssi value: -{rssi}dBm")
                    self.get_channel_rssi()
                    e = datetime.datetime.now()
                    with open("g.txt", "a") as f:
                        f.write(f"Packet RSSI: -{rssi}dBm Current date and time = {e}\n")
            print(f"receive    {json_message} ")
            
            return json_message  # Return the complete JSON string

            # else:
            #     pass
                #print('\x1b[2A',end='\r')


    def receivetemp(self):
        if self.ser.inWaiting() > 0:
            time.sleep(0.5)
            r_buff = self.ser.read(self.ser.inWaiting())

            # Check if the buffer has enough bytes (address + message + RSSI)
            if len(r_buff) < 3:
                print("Incomplete packet")
                return None

            # Extract node address (first two bytes)
            node_address = (r_buff[0] << 8) + r_buff[1]
            print(f"Receive message from address \033[1;32m{node_address} node\033[0m")

            # Extract RSSI (last byte)
            rssi_byte = r_buff[-1]
            rssi = 256 - rssi_byte
            print(f"Packet RSSI value: -{rssi}dBm")

            # Extract message (bytes between address and RSSI)
            message_bytes = r_buff[2:-1]

            try:
                # Decode the message part (excluding address and RSSI)
                message_str = message_bytes.decode('utf-8')
            except UnicodeDecodeError as e:
                print(f"Error decoding message: {e}")
                print(f"Raw message data: {message_bytes}")
                return None

            # Extract JSON from the message string
            try:
                start = message_str.find('{')
                end = message_str.rfind('}') + 1
                if start != -1 and end != -1:
                    json_message = message_str[start:end]
                else:
                    print("No JSON found in message")
                    print(f"Message content: {message_str}")
                    return None
            except Exception as e:
                print(f"Error extracting JSON: {e}")
                return None

            # Logging and additional processing
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            print(f"@ [{current_time}] Received: {json_message}")

            with open("g.txt", "a") as f:
                e = datetime.datetime.now()
                f.write(f"Packet RSSI: -{rssi}dBm Current date and time = {e}\n")

            return json_message
    

             

    def process_received_data(node, received_data):  # New helper function
        if received_data is None:
            return None

        node_address, message_bytes, rssi = received_data  # Unpack the tuple

        try:
            message_str = message_bytes.decode('utf-8', errors='ignore')

            try:
                start = message_str.find('{')
                end = message_str.rfind('}') + 1
                if start!= -1 and end!= -1:
                    json_message = message_str[start:end]
                else:
                    print("Message format error, no JSON found")
                    print("Raw data: " + message_str)
                    return None

            except Exception as e:
                print(f"Error extracting JSON: {e}")
                print("Raw data: " + message_str)
                return None

            print(f"Received from address \033[1;32m{node_address} node\033[0m: {json_message}")
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            print(f"@ [{current_time}] ")
            if node.rssi:
                print(f"RSSI: -{rssi} dBm")

            return json_message

        except UnicodeDecodeError as e:
            print(f"Decoding Error: {e}")
            print(f"Raw bytes: {message_bytes}")  # Print raw bytes for debugging
            return None
    

    def get_channel_rssi(self):
        GPIO.output(self.M1,GPIO.LOW)
        GPIO.output(self.M0,GPIO.LOW)
        time.sleep(0.1)
        self.ser.flushInput()
        self.ser.write(bytes([0xC0,0xC1,0xC2,0xC3,0x00,0x02]))
        time.sleep(0.5)
        re_temp = bytes(5)
        if self.ser.inWaiting() > 0:
            time.sleep(0.1)
            re_temp = self.ser.read(self.ser.inWaiting())
        if re_temp[0] == 0xC1 and re_temp[1] == 0x00 and re_temp[2] == 0x02:
            # print("the current noise rssi value: -{0}dBm".format(256-re_temp[3]))
            f=open("g.txt","a")
            print("Noise RSSI value: -{0}dBm".format(256-re_temp[3]))
            f.write("Noise RSSI: -{0}dBm ".format(256-re_temp[3]))
            f.close()
        else:
            # pass
            print("Receive RSSI value failed!")
            # print("receive rssi value fail: ",re_temp)

    #def relay(self):
    #def wor(self):
    #def remote_config(self):
