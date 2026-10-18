import time
from picamera2 import Picamera2

# --- Configuration ---
FILE_NAME = "test_image.jpg"
RESOLUTION = (1920, 1080)  # Full HD resolution

def test_camera():
    """Initializes the camera, captures an image, and saves it."""
    print("Initializing Picamera2...")
    
    # 1. Initialize the Camera Object
    try:
        # Create a Picamera2 object
        picam2 = Picamera2()
    except RuntimeError as e:
        print("\n--- ERROR ---")
        print("Failed to initialize the camera. Common causes:")
        print("1. Camera not connected to the CSI port.")
        print("2. Camera not enabled in the Raspberry Pi configuration (raspi-config).")
        print(f"Details: {e}")
        return

    # 2. Configure the Camera
    # Use the 'main' stream configuration to set the resolution
    camera_config = picam2.create_still_configuration(main={"size": RESOLUTION})
    picam2.configure(camera_config)

    print(f"Camera configured for resolution: {RESOLUTION[0]}x{RESOLUTION[1]}")
    
    # 3. Start the Camera
    picam2.start()
    print("Camera started. Warming up for 2 seconds...")
    
    # Give the camera a moment to adjust exposure and white balance
    time.sleep(2)

    # 4. Capture and Save the Image
    print(f"Capturing image and saving to {FILE_NAME}...")
    picam2.capture_file(FILE_NAME)

    # 5. Stop the Camera
    picam2.stop()
    print("Camera stopped.")
    
    print("\n✅ Success! Check your current directory for the 'test_image.jpg' file.")
    print("If the file is there and shows an image, your camera module is working.")


if __name__ == "__main__":
    test_camera()