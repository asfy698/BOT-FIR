# hardware/motor_controller.py - Motor control using GPIO
import RPi.GPIO as GPIO


class MotorController:
    """Manages motor control via GPIO pins."""

    # Motor Pin Definitions (BCM Numbering)
    IN1, IN2 = 4, 17  # Left Motor
    IN3, IN4 = 27, 22  # Right Motor (matches the working all1.py wiring)

    def __init__(self):
        print("Initializing Motor Controller...")
        GPIO.setmode(GPIO.BCM)
        self.motor_pins = [self.IN1, self.IN2, self.IN3, self.IN4]
        for pin in self.motor_pins:
            GPIO.setup(pin, GPIO.OUT)
        self.motors_stop()

    def motors_forward(self):
        """Move motors forward."""
        GPIO.output(self.IN1, GPIO.HIGH)
        GPIO.output(self.IN2, GPIO.LOW)
        GPIO.output(self.IN3, GPIO.LOW)
        GPIO.output(self.IN4, GPIO.HIGH)
        print("DEBUG: Motors moving forward.")

    def motors_backward(self):
        """Move motors backward."""
        GPIO.output(self.IN1, GPIO.LOW)
        GPIO.output(self.IN2, GPIO.HIGH)
        GPIO.output(self.IN3, GPIO.HIGH)
        GPIO.output(self.IN4, GPIO.LOW)
        print("DEBUG: Motors moving backward.")

    def motors_turning_L(self):
        """Turn motors left."""
        GPIO.output(self.IN1, GPIO.HIGH)
        GPIO.output(self.IN2, GPIO.LOW)
        GPIO.output(self.IN3, GPIO.HIGH)
        GPIO.output(self.IN4, GPIO.LOW)
        print("DEBUG: Motors turning left.")

    def motors_turning_R(self):
        """Turn motors right."""
        GPIO.output(self.IN1, GPIO.LOW)
        GPIO.output(self.IN2, GPIO.HIGH)
        GPIO.output(self.IN3, GPIO.LOW)
        GPIO.output(self.IN4, GPIO.HIGH)
        print("DEBUG: Motors turning right.")

    def motors_stop(self):
        """Stop all motors."""
        for pin in self.motor_pins:
            GPIO.output(pin, GPIO.LOW)
        print("DEBUG: Motors stopped.")

    def cleanup(self):
        """Clean up GPIO resources."""
        self.motors_stop()
        try:
            GPIO.cleanup()
        except Exception:
            pass

