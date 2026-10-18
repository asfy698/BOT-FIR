# sensors/object_avoid.py

import logging

logger = logging.getLogger("obstacle_avoid")

class ObstacleAvoider:
    def __init__(self, robot, threshold=20):
        self.robot = robot
        self.threshold = threshold
        logger.info("Ultrasonic sensors initialized")

    def is_obstacle_ahead(self):
        """
        Returns True if obstacle detected within threshold (cm)
        """
        try:
            distance = self.robot.get_front_distance()
            print(f"[OBSTACLE] Distance: {distance} cm")
            if distance is None:
                return False
            return distance < self.threshold
        except Exception as e:
            print("[OBSTACLE ERROR]", e)
            return False
