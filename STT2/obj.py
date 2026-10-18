# Robot moves forward continuously
# Stops if obstacle detected by LEFT / CENTER / RIGHT ultrasonic sensors
# L298N motor driver with ENA & ENB JUMPERS ON
# FIXED: Ensures straight forward motion (no turning)

import time
import random          # REMOVE when using real ultrasonic sensors
import RPi.GPIO as GPIO


# ---------------- GPIO SETUP ----------------
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Motor control pins
IN1, IN2 = 4, 17       # Left motor
IN3, IN4 = 27, 22      # Right motor

GPIO.setup([IN1, IN2, IN3, IN4], GPIO.OUT)

# Ensure motors OFF at start
GPIO.output(IN1, GPIO.LOW)
GPIO.output(IN2, GPIO.LOW)
GPIO.output(IN3, GPIO.LOW)
GPIO.output(IN4, GPIO.LOW)


# ---------------- ROBOT CONTROLLER ----------------
class RobotController:

    def move_forward(self):
        """
        FORCE BOTH MOTORS TO MOVE FORWARD
        """
        # Left motor forward
        GPIO.output(IN1, GPIO.HIGH)
        GPIO.output(IN2, GPIO.LOW)

        # Right motor forward
        GPIO.output(IN3, GPIO.LOW)
        GPIO.output(IN4, GPIO.HIGH)

        print("→ Moving FORWARD")

    def stop(self):
        GPIO.output(IN1, GPIO.LOW)
        GPIO.output(IN2, GPIO.LOW)
        GPIO.output(IN3, GPIO.LOW)
        GPIO.output(IN4, GPIO.LOW)

        print("■ Robot STOPPED")

    # ---- Ultrasonic sensor (TEMPORARY SIMULATION) ----
    def get_left_distance(self):
        return random.randint(10, 100)

    def get_center_distance(self):
        return random.randint(10, 100)

    def get_right_distance(self):
        return random.randint(10, 100)


# ---------------- OBSTACLE AVOID ----------------
class ObstacleAvoider:
    def __init__(self, robot, threshold=20):
        self.robot = robot
        self.threshold = threshold
        print("✓ 3 Ultrasonic sensors initialized")

    def obstacle_detected(self):
        left = self.robot.get_left_distance()
        center = self.robot.get_center_distance()
        right = self.robot.get_right_distance()

        print(f"SENSORS → L:{left}cm | C:{center}cm | R:{right}cm")

        return (
            left < self.threshold or
            center < self.threshold or
            right < self.threshold
        )


# ---------------- MAIN LOOP ----------------
def main():
    robot = RobotController()
    obstacle = ObstacleAvoider(robot)

    print("▶ Robot started: Moving forward & checking obstacles")

    try:
        while True:
            # FIRST: Move forward
            robot.move_forward()

            # THEN: Check for obstacle
            if obstacle.obstacle_detected():
                robot.stop()
                print("⚠ Obstacle detected! Robot halted.")
                break

            time.sleep(0.5)   # IMPORTANT: prevents jitter & turning

    except KeyboardInterrupt:
        print("\n✋ Manual stop detected")

    finally:
        robot.stop()
        GPIO.cleanup()
        print("✓ GPIO cleaned. Program ended safely")


if __name__ == "__main__":
    main()
