import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

# PIN DEFINITIONS (BCM Numbering)
# LEFT              
IN1 = 4    # Left Fwd Input
IN2 = 17   # Left Bwd Input
# RIGHT             
IN3 = 27   # Right Bwd Input
IN4 = 22   # Right Fwd Input

GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)
GPIO.setup(IN3, GPIO.OUT)
GPIO.setup(IN4, GPIO.OUT)

# --- MOTOR FUNCTIONS ---

def motors_forward():
    # LEFT FWD
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    # RIGHT FWD
    # Using the corrected logic from the previous exchange: IN3 BWD, IN4 FWD 
    GPIO.output(IN3, GPIO.LOW) 
    GPIO.output(IN4, GPIO.HIGH) 
    print("DEBUG: Motors moving forward.") # Added debug print

def motors_backward():
    # LEFT BWD
    GPIO.output(IN1, GPIO.LOW)  
    GPIO.output(IN2, GPIO.HIGH)
    # RIGHT BWD
    GPIO.output(IN3, GPIO.HIGH) 
    GPIO.output(IN4, GPIO.LOW)  
    print("DEBUG: Motors moving backward.") # Added debug print
    
def motors_turning_L():
    # LEFT FWD 
    GPIO.output(IN1, GPIO.HIGH) 
    GPIO.output(IN2, GPIO.LOW)  
    # RIGHT BWD 
    GPIO.output(IN3, GPIO.HIGH) 
    GPIO.output(IN4, GPIO.LOW)  
    print("DEBUG: Motors turning left.") # Added debug print

def motors_turning_R():
    # LEFT BWD 
    GPIO.output(IN1, GPIO.LOW) 
    GPIO.output(IN2, GPIO.HIGH) 
    # RIGHT FWD 
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)
    print("DEBUG: Motors turning right.") # Added debug print

def motors_stop():
    # ALL LOW for Coast/Float stop
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)
    print("DEBUG: Motors stopped.") # Added debug print
    
# --- Execution Guard: This code only runs when controller.py is run directly ---
if __name__ == "__main__":
    try:
        while True:
            motors_backward()
            time.sleep(2) 
            motors_stop()
            time.sleep(2)
            motors_forward()
            time.sleep(2)
            motors_turning_L()
            time.sleep(2)
            motors_turning_R()
            time.sleep(2)
            
    except KeyboardInterrupt:
        GPIO.cleanup()
