# hardware/camera.py - Camera capture and image utilities
from picamera2 import Picamera2
import time
import os
import config


class Camera:
    """Manages camera operations using Picamera2."""

    def __init__(self):
        self.picam2 = None

    def take_picture(self):
        """Capture a picture and save it to disk."""
        if self.picam2 is None:
            try:
                self.picam2 = Picamera2()
            except RuntimeError as e:
                print(f"ERROR: Failed to initialize camera. {e}")
                return False

        try:
            config_obj = self.picam2.create_still_configuration(
                main={"size": (1920, 1080)}
            )
            self.picam2.configure(config_obj)
            self.picam2.start()
            time.sleep(2)
            self.picam2.capture_file(config.IMAGE_FILE_NAME)
            self.picam2.stop()
            print(f"✅ Image saved to {config.IMAGE_FILE_NAME}")
            return True
        except Exception as e:
            print(f"ERROR: Failed to capture image: {e}")
            return False

    def capture_image(self):
        """Wrapper for take_picture that returns path or None."""
        if self.take_picture():
            return config.IMAGE_FILE_NAME
        return None

