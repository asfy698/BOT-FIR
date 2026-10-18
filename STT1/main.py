# main.py - Entry point for the robot control application

print("MAIN STARTED")   # <- prevents blank terminal confusion

import tkinter as tk
from hardware.robot_controller import RobotController
from gui.robot_face import RobotFace
from stt.stt_manager import STTManager
from sensors.object_avoid import ObstacleAvoider
import config
import current_location_send


def safe_move_forward(robot, obstacle_avoid, gui):
    """Start continuous forward movement with obstacle checking"""
    print("SAFE FORWARD TRIGGERED")
    robot.start_continuous_forward_with_obstacle_check(obstacle_avoid)
    if gui:
        gui.log("Moving forward with obstacle detection", "MOVE")


def stop_robot(robot, gui):
    print("STOP TRIGGERED")
    robot.stop_continuous_forward()
    robot.stop()
    if gui:
        gui.log("Robot stopped", "STOP")


def run_current_location(robot=None, gui=None):
    """Start current location send asynchronously with status callbacks."""
    print("LOCATION SEND TRIGGERED")
    if gui:
        gui.log("Initiating location send...", "LOCATION")
    if robot:
        robot.speak("Sending current location")

    def on_status(msg, tag="LOCATION"):
        if gui:
            gui.log(msg, tag)
        if robot and "sent" in msg.lower() and "location" in msg.lower():
            robot.speak("Location sent successfully")

    current_location_send.send_location_async(status_callback=on_status)


if __name__ == "__main__":
    try:
        print("INITIALIZING ROBOT")

        # ---------------- ROBOT INIT ----------------
        robot = RobotController()
        obstacle_avoid = ObstacleAvoider(robot)

        # ---------------- GUI INIT ----------------
        root = tk.Tk()
        root.title("Robot Control")
        root.geometry("500x500")
        root.lift()
        root.attributes("-topmost", True)
        root.after(500, lambda: root.attributes("-topmost", False))

        face = RobotFace(root, robot)

        # ---------------- SAFE FORWARD BUTTON ----------------
        safe_btn = tk.Button(
            root,
            text="SAFE FORWARD",
            font=("Arial", 12, "bold"),
            bg="green",
            fg="white",
            width=18,
            command=lambda: safe_move_forward(robot, obstacle_avoid, face)
        )
        safe_btn.pack(pady=10)

        # ---------------- KEYBOARD CONTROLS ----------------
        root.bind("<w>", lambda e: safe_move_forward(robot, obstacle_avoid, face))
        root.bind("<s>", lambda e: stop_robot(robot, face))

        # ---------------- LOCATION HANDLER SETUP ----------------
        def handle_location():
            run_current_location(robot=robot, gui=face)

        face.location_callback = handle_location

        # ---------------- STT SETUP ----------------
        stt = STTManager(controller=robot, gui=face)
        stt.location_callback = handle_location

        # Start listening right away when main.py is run
        stt.ignore_transcripts_until = 0.0
        stt.start()
        config.logger.info("STT background started immediately (direct-listening mode)")

        # ---------------- GREETING ----------------
        greeting = "Hi, I am BotFir, speed 1 GHz, memory 1 GB, ready for commands. Welcome to Protospark."
        robot.speak(greeting)
        face.log("System initialized. Ready.", "SYSTEM")

        print("GUI STARTING")
        root.mainloop()

    except KeyboardInterrupt:
        print("SHUTDOWN REQUESTED")

    except Exception as e:
        print("CRITICAL ERROR:", e)

    finally:
        try:
            if 'stt' in locals():
                stt.stop()
        except Exception:
            pass

        if 'robot' in locals():
            robot.cleanup()

        print("PROGRAM EXITED CLEANLY")