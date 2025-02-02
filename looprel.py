#!/usr/bin/python3
import RPi.GPIO as GPIO
import time
import sys

def setup_gpio():
    # Use BCM GPIO numbering
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

def test_pin(pin_number):
    try:
        # Setup the GPIO pin as output
        GPIO.setup(pin_number, GPIO.OUT)
        print(f"\nStarting to toggle GPIO {pin_number}")
        print("Press CTRL+C to stop")
        
        while True:
            # Turn ON
            GPIO.output(pin_number, True)
            print(f"GPIO {pin_number}: ON")
            time.sleep(1)
            
            # Turn OFF
            GPIO.output(pin_number, False)
            print(f"GPIO {pin_number}: OFF")
            time.sleep(1)
            
    except Exception as e:
        print(f"\nError with GPIO {pin_number}: {str(e)}")
        return False
    
    return True

def main():
    setup_gpio()
    
    while True:
        try:
            # Get pin number from user
            pin_str = input("\nEnter GPIO number to test (or 'q' to quit): ")
            
            # Check for quit command
            if pin_str.lower() == 'q':
                print("Exiting program...")
                break
            
            # Convert input to integer
            pin = int(pin_str)
            
            # List of pins used by LoRa HAT
            lora_pins = [8, 14, 15, 17, 23, 24, 25]
            
            # Warn if trying to use a LoRa HAT pin
            if pin in lora_pins:
                print(f"\nWarning: GPIO {pin} is used by the LoRa HAT!")
                confirm = input("Are you sure you want to continue? (y/n): ")
                if confirm.lower() != 'y':
                    continue
            
            test_pin(pin)
            
        except KeyboardInterrupt:
            print("\nTest stopped by user")
            continue
            
        except ValueError:
            print("\nPlease enter a valid number")
            continue
            
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            continue

    # Clean up
    GPIO.cleanup()
    print("GPIO cleanup completed")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        GPIO.cleanup()
