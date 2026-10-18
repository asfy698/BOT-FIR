# hardware/robot_controller.py - Facade for all robot hardware and services
from hardware.motor_controller import MotorController
from hardware.camera import Camera
from services.gemini_client import GeminiClient
from services.vision_api import VisionAPI
import os
import config


class RobotController:
    """Facade that manages all hardware and API interactions for the robot."""

    def __init__(self):
        print("Initializing Robot Controller...")
        self.motor_controller = MotorController()
        self.camera = Camera()
        self.gemini_client = GeminiClient()
        self.vision_api = VisionAPI()

    # --- MOTOR CONTROL FUNCTIONS (delegate to MotorController) ---
    def motors_forward(self):
        self.motor_controller.motors_forward()

    def motors_backward(self):
        self.motor_controller.motors_backward()

    def motors_turning_L(self):
        self.motor_controller.motors_turning_L()

    def motors_turning_R(self):
        self.motor_controller.motors_turning_R()

    def motors_stop(self):
        self.motor_controller.motors_stop()

    # --- CAMERA FUNCTIONS (delegate to Camera) ---
    def take_picture(self):
        return self.camera.take_picture()

    def capture_image(self):
        """Wrapper for take_picture that returns path or None"""
        return self.camera.capture_image()

    def get_image_data_uri(self, image_path=None):
        """Get image data URI (delegates to VisionAPI)."""
        if image_path is None:
            image_path = config.IMAGE_FILE_NAME
        return self.vision_api.get_image_data_uri(image_path)

    def detect_objects(self):
        """Analyze image using Hugging Face API."""
        return self.vision_api.detect_objects(config.IMAGE_FILE_NAME)

    def analyze_image(self, image_path):
        """Wrapper for detect_objects"""
        return self.vision_api.analyze_image(image_path)

    # --- GEMINI FUNCTIONS (delegate to GeminiClient) ---
    def chat_with_gemini(self, prompt):
        """Chat with Gemini API"""
        return self.gemini_client.chat(prompt)

    def speak(self, text):
        """Generate and play text-to-speech"""
        self.gemini_client.speak(text)

    # --- CLEANUP ---
    def cleanup(self):
        print("Cleaning up...")
        self.motor_controller.cleanup()
        if os.path.exists(config.IMAGE_FILE_NAME):
            try:
                os.remove(config.IMAGE_FILE_NAME)
            except Exception:
                pass
        print("Done.")

