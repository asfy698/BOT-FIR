# hardware/ultrasonic_sensor.py - HC-SR04 Ultrasonic Sensor Control
import RPi.GPIO as GPIO
import time


class UltrasonicSensor:
    """
    Controls a single HC-SR04 ultrasonic distance sensor.
    
    Wiring:
    - VCC -> 5V (Pin 2)
    - GND -> GND (Pin 6)
    - Trig -> GPIO pin (specified in init)
    - Echo -> GPIO pin (specified in init)
    """
    
    def __init__(self, trig_pin, echo_pin):
        """
        Initialize ultrasonic sensor.
        
        Args:
            trig_pin: GPIO pin number for Trigger (BCM numbering)
            echo_pin: GPIO pin number for Echo (BCM numbering)
        """
        self.trig_pin = trig_pin
        self.echo_pin = echo_pin
        
        # Setup GPIO pins
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.trig_pin, GPIO.OUT)
        GPIO.setup(self.echo_pin, GPIO.IN)
        
        # Initialize trigger to LOW
        GPIO.output(self.trig_pin, GPIO.LOW)
        time.sleep(0.1)  # Allow sensor to settle
        
    def get_distance(self):
        """
        Measure distance in centimeters.
        Returns distance in cm, or 400 if timeout/error (max range ~400cm).
        """
        try:
            # Send trigger pulse (10 microseconds)
            GPIO.output(self.trig_pin, GPIO.HIGH)
            time.sleep(0.00001)  # 10 microseconds
            GPIO.output(self.trig_pin, GPIO.LOW)
            
            # Wait for echo to go HIGH
            timeout_start = time.time()
            while GPIO.input(self.echo_pin) == GPIO.LOW:
                if time.time() - timeout_start > 0.1:  # 100ms timeout
                    return 400  # Timeout - assume far away
                pass
            
            # Measure echo pulse duration
            pulse_start = time.time()
            timeout_start = time.time()
            while GPIO.input(self.echo_pin) == GPIO.HIGH:
                if time.time() - timeout_start > 0.1:  # 100ms timeout
                    return 400  # Timeout - assume far away
                pass
            pulse_end = time.time()
            
            # Calculate distance
            pulse_duration = pulse_end - pulse_start
            # Speed of sound = 34300 cm/s
            # Distance = (pulse_duration * speed) / 2 (divide by 2 because sound travels to object and back)
            distance = (pulse_duration * 34300) / 2
            
            # Clamp to reasonable range (2cm to 400cm)
            distance = max(2, min(400, distance))
            
            return distance
            
        except Exception as e:
            print(f"Error reading ultrasonic sensor (Trig:{self.trig_pin}, Echo:{self.echo_pin}): {e}")
            return 400  # Return max distance on error
    
    def cleanup(self):
        """Clean up GPIO pins (optional, GPIO.cleanup() handles this)"""
        pass


class UltrasonicSensorArray:
    """
    Manages 3 ultrasonic sensors (Left, Center, Right).
    
    Default GPIO pins (BCM numbering):
    - Left:   Trig=19, Echo=21
    - Center: Trig=20, Echo=25
    - Right:  Trig=5,  Echo=6
    
    Note: GPIO 4, 17, 22, 27 are used by motors
    """
    
    def __init__(self, left_trig=19, left_echo=21, 
                       center_trig=20, center_echo=25,
                       right_trig=5, right_echo=6):
        """
        Initialize all three ultrasonic sensors.
        
        Args:
            left_trig, left_echo: GPIO pins for left sensor
            center_trig, center_echo: GPIO pins for center sensor
            right_trig, right_echo: GPIO pins for right sensor
        """
        print("Initializing 3 ultrasonic sensors...")
        
        self.left_sensor = UltrasonicSensor(left_trig, left_echo)
        self.center_sensor = UltrasonicSensor(center_trig, center_echo)
        self.right_sensor = UltrasonicSensor(right_trig, right_echo)
        
        print(f"✓ Left sensor:   Trig=GPIO{left_trig}, Echo=GPIO{left_echo}")
        print(f"✓ Center sensor: Trig=GPIO{center_trig}, Echo=GPIO{center_echo}")
        print(f"✓ Right sensor:  Trig=GPIO{right_trig}, Echo=GPIO{right_echo}")
    
    def get_left_distance(self):
        """Get distance from left sensor in cm"""
        return self.left_sensor.get_distance()
    
    def get_center_distance(self):
        """Get distance from center sensor in cm"""
        return self.center_sensor.get_distance()
    
    def get_right_distance(self):
        """Get distance from right sensor in cm"""
        return self.right_sensor.get_distance()
    
    def cleanup(self):
        """Clean up all sensors"""
        pass  # GPIO cleanup handled elsewhere

