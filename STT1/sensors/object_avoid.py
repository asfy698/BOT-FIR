# Robot moves forward continuously
# Stops if obstacle detected by LEFT / CENTER / RIGHT ultrasonic sensors
# Stops if edge detected by CENTER ultrasonic sensor ONLY
# L298N motor driver with ENA & ENB JUMPERS ON
# FIXED: Ensures straight forward motion (no turning)

import time
import random          # REMOVE when using real ultrasonic sensors

# ---------------- OBSTACLE & EDGE AVOID ----------------

class ObstacleAvoider:

    def __init__(self, robot, threshold=50, edge_threshold=100):
        self.robot = robot
        self.threshold = threshold
        self.edge_threshold = edge_threshold
        print(f"??? Ultrasonic sensor initialized (Obstacle threshold: {self.threshold}cm, Edge threshold: {self.edge_threshold}cm | Edge sensor: CENTER ONLY)")

    def obstacle_detected(self):
        """
        Check for obstacles with multiple readings to reduce false positives.
        Takes 3 readings and uses median value for each sensor (more stable).
        Uses ALL 3 sensors (LEFT, CENTER, RIGHT) for obstacle avoidance.
        """
        # Take multiple readings for stability
        readings = []
        for _ in range(3):
            left = self.robot.get_left_distance()
            center = self.robot.get_center_distance()
            right = self.robot.get_right_distance()
            readings.append((left, center, right))
        
        # Use the median reading for each sensor (more stable than single reading)
        left_values = [r[0] for r in readings]
        center_values = [r[1] for r in readings]
        right_values = [r[2] for r in readings]
        
        left = sorted(left_values)[1]  # median
        center = sorted(center_values)[1]  # median
        right = sorted(right_values)[1]  # median
        
        print(f"SENSORS ??? L:{left}cm | C:{center}cm | R:{right}cm")

        # Stop when ANY ONE sensor detects an obstacle below the threshold.
        distances = {
            "LEFT": left,
            "CENTER": center,
            "RIGHT": right,
        }
        blocked_sensors = [
            name for name, distance in distances.items()
            if distance < self.threshold
        ]
        obstacle = bool(blocked_sensors)

        if obstacle:
            print(
                f"OBSTACLE DETECTED by {', '.join(blocked_sensors)} "
                f"(stop threshold: {self.threshold}cm)"
            )
        
        return obstacle

    def is_obstacle_ahead(self):
        """Alias for obstacle_detected() for compatibility"""
        return self.obstacle_detected()

    def edge_detected(self):
        """
        Check for edges / cliffs / table drop-offs using ONLY the CENTER ultrasonic sensor.
        Takes 3 readings of the center sensor and uses median value for stability.
        An edge is detected when the center distance exceeds edge_threshold (drop-off / void).
        Left and Right sensors are NOT used for edge detection, only for obstacle avoidance.
        """
        # Take 3 readings from CENTER sensor only
        readings = [self.robot.get_center_distance() for _ in range(3)]
        center = sorted(readings)[1]  # median

        edge = center > self.edge_threshold
        if edge:
            print(
                f"EDGE DETECTED by CENTER sensor: {center}cm "
                f"(edge threshold: {self.edge_threshold}cm)"
            )
        return edge

    def is_edge_ahead(self):
        """Alias for edge_detected() for compatibility"""
        return self.edge_detected()
