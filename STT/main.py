# main.py
import threading
import queue
import time
import logging
import cv2
import re

import tkinter as tk
from hardware.robot_controller import RobotController
from gui.robot_face import RobotFace
from stt.stt_manager import STTManager
import config
import object_avoid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("robot")

# Queue for STT transcripts
command_queue = queue.Queue()

# Command patterns
COMMAND_PATTERNS = {
    "MOVE_FORWARD": [r"\b(move forward|go forward|forward|ahead)\b"],
    "MOVE_BACKWARD": [r"\b(move back|backward|reverse)\b"],
    "TURN_LEFT": [r"\b(turn left|left)\b"],
    "TURN_RIGHT": [r"\b(turn right|right)\b"],
    "STOP": [r"\b(stop|halt|pause)\b"],
    "EXPLORE": [r"\b(explore|scan area)\b"],
    "WHAT_DID_YOU_SEE": [r"\b(what did you see|what did u c|what did you find)\b"],
}

def parse_command(text: str):
    txt = text.lower()

    # Wake word
    if "hey bot" in txt:
        txt = txt.replace("hey bot", "")

        for cmd, patterns in COMMAND_PATTERNS.items():
            for p in patterns:
                if re.search(p, txt):
                    return cmd
    return None


# =========================
# STT callback
# =========================
def on_transcript_callback(transcript):
    logger.info(f"Transcript: {transcript}")
    command_queue.put(transcript)


# =========================
# Explore Logic
# =========================
last_seen = None

def explore_environment():
    global last_seen

    controller.stop()
    time.sleep(0.2)

    # capture camera frame
    cam = cv2.VideoCapture(0)
    ret, frame = cam.read()
    cam.release()

    if not ret:
        tts.speak("Camera error")
        return

    detections = obj_det.detect_image(frame)

    if not detections:
        tts.speak("I did not see anything")
        return

    # choose highest confidence
    best = max(detections, key=lambda d: d["confidence"])
    label = best["label"]
    conf = best["confidence"]
    bbox = best["bbox"]

    # draw circle
    x1, y1, x2, y2 = bbox
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    cv2.circle(frame, (cx, cy), 40, (0, 255, 0), 3)

    # save result
    cv2.imwrite("last_explore.png", frame)

    tts.speak(f"I see {label} with {int(conf * 100)} percent confidence")

    last_seen = {"label": label, "confidence": conf}


def describe_last_seen():
    if not last_seen:
        tts.speak("I have not explored anything yet")
    else:
        tts.speak(
            f"Previously I saw {last_seen['label']} with {int(last_seen['confidence'] * 100)} percent confidence"
        )


# =========================
# Worker thread
# =========================
def command_worker():
    while True:
        text = command_queue.get()

        if text is None:
            break

        cmd = parse_command(text)
        if not cmd:
            continue

        logger.info("Command = " + cmd)

        if cmd == "MOVE_FORWARD":
            tts.speak("Moving forward")
            # Use obstacle avoidance for safe forward movement
            success = obstacle_avoid.safe_move_forward(controller, duration=0.5, check_interval=0.1)
            if not success:
                tts.speak("Obstacle detected, avoiding")

        elif cmd == "MOVE_BACKWARD":
            tts.speak("Moving backward")
            # Check for obstacles behind before moving backward
            controller.move_backward(0.5)

        elif cmd == "TURN_LEFT":
            tts.speak("Turning left")
            # Check path before turning
            is_clear, distances, _ = obstacle_avoid.check_path_clear()
            if not is_clear:
                logger.info(f"Obstacle detected before turn. Distances: {distances}")
            controller.turn_left(0.4)

        elif cmd == "TURN_RIGHT":
            tts.speak("Turning right")
            # Check path before turning
            is_clear, distances, _ = obstacle_avoid.check_path_clear()
            if not is_clear:
                logger.info(f"Obstacle detected before turn. Distances: {distances}")
            controller.turn_right(0.4)

        elif cmd == "STOP":
            tts.speak("Stopping")
            controller.stop()

        elif cmd == "EXPLORE":
            tts.speak("Exploring now")
            explore_environment()

        elif cmd == "WHAT_DID_YOU_SEE":
            describe_last_seen()

        time.sleep(0.2)


# =========================
# Start Program
# =========================
if __name__ == "__main__":
    worker_thread = threading.Thread(target=command_worker, daemon=True)
    worker_thread.start()

    #stt.start_stream(on_transcript_callback)
