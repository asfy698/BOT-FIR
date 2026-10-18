try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# robot_main.py - Unified Robot Control Script (Hey Bot + Voice-to-GUI Textbox)
# Save as robot_main.py
# --- 1. RASPBERRY PI HARDWARE & MOTOR CONTROL IMPORTS ---
import RPi.GPIO as GPIO
import time
import subprocess  # For playing audio

# --- 2. CAMERA IMPORTS ---
from picamera2 import Picamera2
import os
import re  # For sanitizing filenames

# --- 3. OBJECT DETECTION (HUGGING FACE) IMPORTS ---
import requests
import base64
import mimetypes

# --- 4. TEXT-TO-SPEECH (GEMINI API) IMPORTS ---
from google import genai
from google.genai import types
import struct

# --- 5. GUI (FACE) IMPORTS ---
import tkinter as tk
from tkinter import ttk, scrolledtext
from PIL import Image, ImageTk
import datetime

# --- 6. ASSEMBLYAI (STT) IMPORTS ---
import assemblyai as aai
from assemblyai.streaming.v3 import (
    BeginEvent,
    StreamingClient,
    StreamingClientOptions,
    StreamingError,
    StreamingEvents,
    StreamingParameters,
    StreamingSessionParameters,
    TerminationEvent,
    TurnEvent,
)
import logging
import threading
import queue

# ---------------- CONFIGURATION ----------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
HF_API_KEY = os.getenv("HF_API_KEY", "")
HF_API_URL = "https://router.huggingface.co/v1/chat/completions"
IMAGE_FILE_NAME = "captured_image.jpg"
TTS_CACHE_DIR = "tts_cache"
ASSEMBLY_API_KEY = os.getenv("ASSEMBLY_API_KEY", "")

os.makedirs(TTS_CACHE_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("robot_main")

# ---------------- RobotController ----------------
class RobotController:
    """Manages all hardware and API interactions for the robot."""

    IN1, IN2 = 4, 17  # Left Motor
    IN3, IN4 = 27, 22  # Right Motor

    def __init__(self):
        print("Initializing Robot Controller...")
        GPIO.setmode(GPIO.BCM)
        self.motor_pins = [self.IN1, self.IN2, self.IN3, self.IN4]
        for pin in self.motor_pins:
            GPIO.setup(pin, GPIO.OUT)
        self.motors_stop()
        self.gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        self.picam2 = None

    def motors_forward(self):
        GPIO.output(self.IN1, GPIO.HIGH)
        GPIO.output(self.IN2, GPIO.LOW)
        GPIO.output(self.IN3, GPIO.LOW)
        GPIO.output(self.IN4, GPIO.HIGH)
        print("DEBUG: Motors moving forward.")

    def motors_backward(self):
        GPIO.output(self.IN1, GPIO.LOW)
        GPIO.output(self.IN2, GPIO.HIGH)
        GPIO.output(self.IN3, GPIO.HIGH)
        GPIO.output(self.IN4, GPIO.LOW)
        print("DEBUG: Motors moving backward.")

    def motors_turning_L(self):
        GPIO.output(self.IN1, GPIO.HIGH)
        GPIO.output(self.IN2, GPIO.LOW)
        GPIO.output(self.IN3, GPIO.HIGH)
        GPIO.output(self.IN4, GPIO.LOW)
        print("DEBUG: Motors turning left.")

    def motors_turning_R(self):
        GPIO.output(self.IN1, GPIO.LOW)
        GPIO.output(self.IN2, GPIO.HIGH)
        GPIO.output(self.IN3, GPIO.LOW)
        GPIO.output(self.IN4, GPIO.HIGH)
        print("DEBUG: Motors turning right.")

    def motors_stop(self):
        for pin in self.motor_pins:
            GPIO.output(pin, GPIO.LOW)
        print("DEBUG: Motors stopped.")

    def take_picture(self):
        if self.picam2 is None:
            try:
                self.picam2 = Picamera2()
            except RuntimeError as e:
                print(f"ERROR: Failed to initialize camera. {e}")
                return False
        try:
            config = self.picam2.create_still_configuration(main={"size": (1920, 1080)})
            self.picam2.configure(config)
            self.picam2.start()
            time.sleep(2)
            self.picam2.capture_file(IMAGE_FILE_NAME)
            self.picam2.stop()
            print(f"✅ Image saved to {IMAGE_FILE_NAME}")
            return True
        except Exception as e:
            print(f"ERROR: Failed to capture image: {e}")
            return False

    def capture_image(self):
        if self.take_picture():
            return IMAGE_FILE_NAME
        return None

    def get_image_data_uri(self, image_path):
        if not os.path.exists(image_path):
            return None
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_type = "image/jpeg"
        with open(image_path, "rb") as img:
            encoded = base64.b64encode(img.read()).decode("utf-8")
            return f"data:{mime_type};base64,{encoded}"

    def detect_objects(self):
        data_uri = self.get_image_data_uri(IMAGE_FILE_NAME)
        if not data_uri:
            return "Could not read image."
        payload = {
            "model": "zai-org/GLM-4.5V:novita",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "Describe this scene in one short sentence."},
                {"type": "image_url", "image_url": {"url": data_uri}}
            ]}],
            "max_tokens": 100,
        }
        headers = {"Authorization": f"Bearer {HF_API_KEY}", "Content-Type": "application/json"}
        try:
            r = requests.post(HF_API_URL, headers=headers, json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            try:
                content = data["choices"][0]["message"]["content"]
            except Exception:
                content = str(data)
            return content
        except Exception as e:
            return f"Object detection error: {e}"

    def analyze_image(self, image_path):
        return self.detect_objects()

    def chat_with_gemini(self, prompt):
        try:
            model = "gemini-2.0-flash"
            response = self.gemini_client.models.generate_content(model=model, contents=prompt)
            return response.text
        except Exception as e:
            print(f"Gemini Chat Error: {e}")
            return "I am having trouble connecting to my brain."

    def _convert_to_wav(self, audio_data: bytes, mime_type: str) -> bytes:
        bits_per_sample = 16
        sample_rate = 24000
        num_channels = 1
        data_size = len(audio_data)
        block_align = num_channels * (bits_per_sample // 8)
        byte_rate = sample_rate * block_align
        chunk_size = 36 + data_size
        header = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", chunk_size, b"WAVE", b"fmt ", 16, 1,
                            num_channels, sample_rate, byte_rate, block_align, bits_per_sample, b"data", data_size)
        return header + audio_data

    def _get_cache_filename(self, text):
        clean_text = re.sub(r'[^a-zA-Z0-9]', '_', text)
        clean_text = re.sub(r'_+', '_', clean_text)
        clean_text = clean_text.strip('_')
        return clean_text[:60] + ".wav"

    def speak(self, text):
        print(f"TTS Request: {text}")
        filename = self._get_cache_filename(text)
        cache_path = os.path.join(TTS_CACHE_DIR, filename)
        if os.path.exists(cache_path):
            print(f"✓ Playing from cache: {cache_path}")
            try:
                subprocess.run(["aplay", cache_path])
                return
            except Exception as e:
                print(f"WARNING: Could not play cached audio: {e}")
        print("Generating new audio via Gemini API...")
        model = "gemini-2.5-flash-preview-tts"
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=text)])]
        config = types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Umbriel"))))
        try:
            data_buffer = b""
            for chunk in self.gemini_client.models.generate_content_stream(model=model, contents=contents, config=config):
                if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                    part = chunk.candidates[0].content.parts[0]
                    if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.data:
                        data_buffer += part.inline_data.data
            if not data_buffer:
                print("ERROR: Empty audio buffer from API")
                return
            wav = self._convert_to_wav(data_buffer, "audio/L16;rate=24000")
            with open(cache_path, "wb") as f:
                f.write(wav)
            print(f"✓ Audio cached to: {cache_path}")
            subprocess.run(["aplay", cache_path])
        except Exception as e:
            print(f"TTS Error: {e}")

    def cleanup(self):
        print("Cleaning up...")
        self.motors_stop()
        try:
            GPIO.cleanup()
        except Exception:
            pass
        if os.path.exists(IMAGE_FILE_NAME):
            try:
                os.remove(IMAGE_FILE_NAME)
            except Exception:
                pass
        print("Done.")

# ---------------- RobotFace (GUI) ----------------
class RobotFace(tk.Frame):
    def __init__(self, master, controller):
        tk.Frame.__init__(self, master)
        self.controller = controller
        self.master = master

        self.colors = {
            "bg": "#F2F0EB", "header": "#1F1F1F", "card": "#FFFFFF", "accent": "#FFB300",
            "text_dark": "#212121", "text_light": "#757575", "terminal_bg": "#121212",
            "terminal_fg": "#00E676", "danger": "#D32F2F"
        }

        master.title("BotFir AI - Production Dashboard")
        master.geometry("800x480")
        master.config(bg=self.colors["bg"])

        screen_width = master.winfo_screenwidth()
        screen_height = master.winfo_screenheight()
        is_small_screen = screen_width < 800 or screen_height < 600
        
        if is_small_screen:
            face_size = min(int(screen_height * 0.3), 120)
            title_font = ("Helvetica", 12, "bold")
            header_height = 35
            pad_small, pad_med = 2, 5
            btn_font = ("Helvetica", 9, "bold")
            log_height = 6
        else:
            face_size = min(int(screen_width * 0.3), 220)
            title_font = ("Helvetica", 16, "bold")
            header_height = 50
            pad_small, pad_med = 5, 10
            btn_font = ("Helvetica", 12, "bold")
            log_height = 10

        FACE_SIZE = (face_size, face_size)
        self.screen_width = screen_width
        self.screen_height = screen_height

        try:
            self.mouth_closed = ImageTk.PhotoImage(Image.open("face_closed.png").resize(FACE_SIZE, Image.Resampling.LANCZOS))
            self.mouth_open = ImageTk.PhotoImage(Image.open("face_open.png").resize(FACE_SIZE, Image.Resampling.LANCZOS))
        except:
            self.mouth_closed = self.mouth_open = None

        # Header
        header = tk.Frame(master, bg=self.colors["header"], height=header_height)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        tk.Label(header, text="BOTFIR AI", fg=self.colors["accent"], bg=self.colors["header"], font=title_font).pack(side="left", padx=pad_med)
        tk.Label(header, text="| PRODUCTION SYSTEM v2.1", fg="#888", bg=self.colors["header"], font=("Helvetica", 10)).pack(side="left")
        self.status_indicator = tk.Label(header, text="● ONLINE", fg=self.colors["terminal_fg"], bg=self.colors["header"], font=("Helvetica", 10, "bold"))
        self.status_indicator.pack(side="right", padx=pad_med)

        # Dashboard
        dashboard = tk.Frame(master, bg=self.colors["bg"])
        dashboard.pack(fill="both", expand=True, padx=pad_med, pady=pad_med)

        # Left Column
        left_col = tk.Frame(dashboard, bg=self.colors["bg"], width=int(screen_width*0.4))
        left_col.pack(side="left", fill="both", expand=True, padx=(0, pad_small))

        face_card = tk.Frame(left_col, bg=self.colors["card"], relief="flat", bd=1)
        face_card.pack(fill="both", expand=True, pady=(0, pad_small))
        self.face_label = tk.Label(face_card, bg=self.colors["card"])
        if self.mouth_closed:
            self.face_label.config(image=self.mouth_closed)
        else:
            self.face_label.config(text="[VISUAL SYSTEM]", fg=self.colors["accent"])
        self.face_label.pack(expand=True)

        telemetry_card = tk.Frame(left_col, bg=self.colors["card"], height=100)
        telemetry_card.pack(fill="x")
        t_grid = tk.Frame(telemetry_card, bg=self.colors["card"])
        t_grid.pack(fill="both", padx=pad_med, pady=pad_med)

        def add_stat(parent, label, value, row, col):
            tk.Label(parent, text=label, fg=self.colors["text_light"], bg=self.colors["card"], font=("Helvetica", 8)).grid(row=row, column=col, sticky="w")
            tk.Label(parent, text=value, fg=self.colors["text_dark"], bg=self.colors["card"], font=("Helvetica", 10, "bold")).grid(row=row+1, column=col, sticky="w", padx=(0, 15))

        add_stat(t_grid, "CPU SPEED", "1.0 GHz", 0, 0)
        add_stat(t_grid, "MEMORY", "1.0 GB", 0, 1)
        add_stat(t_grid, "MOTOR STATUS", "STANDBY", 0, 2)

        # Right Column
        right_col = tk.Frame(dashboard, bg=self.colors["bg"])
        right_col.pack(side="right", fill="both", expand=True, padx=(pad_small, 0))

        # Logs
        log_frame = tk.Frame(right_col, bg=self.colors["terminal_bg"], relief="sunken", bd=1)
        log_frame.pack(fill="both", expand=True, pady=(0, pad_small))
        tk.Label(log_frame, text="SYSTEM LOGS >_", fg=self.colors["accent"], bg=self.colors["terminal_bg"], font=("Courier", 8), anchor="w").pack(fill="x", padx=2)
        self.log_display = scrolledtext.ScrolledText(log_frame, bg=self.colors["terminal_bg"], fg=self.colors["terminal_fg"], font=("Courier", 9),
                                                   height=log_height, state="disabled", relief="flat")
        self.log_display.pack(fill="both", expand=True, padx=2, pady=2)

        # Input (VOICE APPEARS HERE AFTER "hey bot")
        input_frame = tk.Frame(right_col, bg=self.colors["card"], height=40)
        input_frame.pack(fill="x", pady=(0, pad_small))
        self.command_input = tk.Entry(input_frame, bg=self.colors["card"], fg=self.colors["text_dark"], font=("Helvetica", 12), relief="flat")
        self.command_input.pack(fill="both", expand=True, padx=pad_med, pady=5)
        self.command_input.bind("<Return>", self.handle_command)

        # Control Buttons
        control_pad = tk.Frame(right_col, bg=self.colors["bg"])
        control_pad.pack(fill="x")
        for i in range(3): control_pad.columnconfigure(i, weight=1)

        btn_style = {"font": btn_font, "relief": "flat", "bd": 0, "cursor": "hand2", "bg": self.colors["card"], "fg": self.colors["text_dark"],
                    "activebackground": self.colors["accent"], "activeforeground": "black"}

        tk.Button(control_pad, text="▲", command=lambda: self.quick_command("forward"), **btn_style).grid(row=0, column=1, sticky="ew", padx=1, pady=1, ipady=5)
        tk.Button(control_pad, text="◄", command=lambda: self.quick_command("left"), **btn_style).grid(row=1, column=0, sticky="ew", padx=1, pady=1, ipady=5)
        tk.Button(control_pad, text="STOP", command=lambda: self.quick_command("stop"), font=btn_font, relief="flat", bg=self.colors["danger"], fg="white",
                 activebackground="#B71C1C", activeforeground="white").grid(row=1, column=1, sticky="ew", padx=1, pady=1, ipady=5)
        tk.Button(control_pad, text="►", command=lambda: self.quick_command("right"), **btn_style).grid(row=1, column=2, sticky="ew", padx=1, pady=1, ipady=5)
        tk.Button(control_pad, text="▼", command=lambda: self.quick_command("backward"), **btn_style).grid(row=2, column=1, sticky="ew", padx=1, pady=1, ipady=5)
        tk.Button(control_pad, text="SCAN", command=lambda: self.quick_command("analyze"), font=btn_font, relief="flat", bg=self.colors["accent"], fg="black").grid(row=2, column=2, sticky="ew", padx=1, pady=1, ipady=5)

    def set_voice_input(self, text):
        """Voice command appears here after 'hey bot' - ready for Enter"""
        self.command_input.delete(0, tk.END)
        self.command_input.insert(0, text)
        self.log(f"🎤 Voice command ready: {text} (Press Enter to execute)", "VOICE")

    def log(self, message, tag="INFO"):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] [{tag}] {message}\n"
        self.log_display.config(state="normal")
        self.log_display.insert(tk.END, full_msg)
        self.log_display.see(tk.END)
        self.log_display.config(state="disabled")
        self.master.update()

    def quick_command(self, cmd):
        self.command_input.delete(0, tk.END)
        self.command_input.insert(0, cmd)
        self.handle_command()

    def animate_mouth(self, duration=4):
        if not self.mouth_open: return
        self.face_label.config(image=self.mouth_open)
        self.master.update()
        time.sleep(duration)
        self.face_label.config(image=self.mouth_closed)
        self.master.update()

    def display_captured_image(self):
        if os.path.exists(IMAGE_FILE_NAME):
            try:
                img = Image.open(IMAGE_FILE_NAME)
                w, h = int(self.screen_width * 0.35), int(self.screen_height * 0.35)
                img.thumbnail((w, h), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.face_label.config(image=photo)
                self.face_label.image = photo
                self.log("Image displayed on HUD.", "VISUAL")
            except Exception as e:
                self.log(f"Display Error: {e}", "ERROR")

    def restore_face(self):
        if self.mouth_closed:
            self.face_label.config(image=self.mouth_closed)
            self.face_label.image = self.mouth_closed

    def handle_command(self, event=None):
        cmd = self.command_input.get().lower().strip()
        print(f"DEBUG: handle_command called. cmd: '{cmd}'")
        if not cmd:
            print("DEBUG: Empty command, ignoring.")
            return

        self.command_input.delete(0, tk.END)
        self.log(f"Executing: {cmd}", "USER")

        if any(x in cmd for x in ["stop", "halt", "brake"]):
            self.controller.motors_stop()
            self.log("Motors STOPPED", "MOTOR")
        elif any(x in cmd for x in ["forward", "front", "go", "up"]):
            self.controller.motors_forward()
            self.log("Moving FORWARD", "MOTOR")
            self.animate_mouth(4)
            self.controller.motors_stop()
        elif any(x in cmd for x in ["backward", "back", "reverse", "down"]):
            self.controller.motors_backward()
            self.log("Moving BACKWARD", "MOTOR")
            self.animate_mouth(4)
            self.controller.motors_stop()
        elif any(x in cmd for x in ["left", "turn left"]):
            self.controller.motors_turning_L()
            self.log("Turning LEFT", "MOTOR")
            self.animate_mouth(0.5)
            self.controller.motors_stop()
        elif any(x in cmd for x in ["right", "turn right"]):
            self.controller.motors_turning_R()
            self.log("Turning RIGHT", "MOTOR")
            self.animate_mouth(0.5)
            self.controller.motors_stop()
        elif any(x in cmd for x in ["analyze", "vision", "see", "scan", "what is this", "what's this"]):
            self.log("Initializing Vision Scan...", "SYSTEM")
            image_path = self.controller.capture_image()
            if image_path:
                self.display_captured_image()
                self.log("Image Captured. Analyzing...", "AI")
                description = self.controller.analyze_image(image_path)
                self.log(f"Analysis: {description}", "AI")
                self.controller.speak(f"I see {description}")
                self.master.after(5000, self.restore_face)
            else:
                self.log("Camera Capture Failed", "ERROR")
                self.controller.speak("I could not capture an image.")
        elif any(x in cmd for x in ["exit", "quit", "shutdown"]):
            self.log("Shutdown Sequence Initiated...", "SYSTEM")
            self.master.after(1000, self.master.destroy)
        else:
            self.log("Processing Query...", "AI")
            try:
                response = self.controller.chat_with_gemini(cmd)
                self.log(f"Response: {response}", "GEMINI")
            except Exception as e:
                self.log(f"API Error: {e}", "ERROR")

# ---------------- STT Manager (Hey Bot Hotword) ----------------
class STTManager:
    """Hey Bot hotword → shows next command in GUI textbox"""

    def __init__(self, controller: RobotController, gui: RobotFace):
        self.controller = controller
        self.gui = gui
        self.queue = queue.Queue()
        self.awaiting_command = False
        self.awaiting_since = None
        self.timeout_seconds = 10
        self.running = False
        self.client = None
        aai.settings.api_key = ASSEMBLY_API_KEY

    def on_begin(self, client, event: BeginEvent):
        logger.info(f"STT session started: {event.id}")

    def on_turn(self, client, event: TurnEvent):
        if event.end_of_turn and event.transcript:
            transcript = event.transcript.strip().lower()
            logger.info(f"Transcript: '{transcript}'")
            
            if not self.awaiting_command:
                # Check for hotword
                if "hay bot" in transcript or "haybot" in transcript:
                    logger.info("🎤 Hotword 'hey bot' detected!")
                    self.controller.speak("Yes fir?")
                    self.awaiting_command = True
                    self.awaiting_since = time.time()
                    self.gui.log("🔴 Listening for your command...", "VOICE")
                else:
                    logger.debug("Background speech ignored (no hotword)")
            else:
                # Got command after hotword - put in GUI textbox
                if time.time() - self.awaiting_since > self.timeout_seconds:
                    logger.info("Command timeout - resetting")
                    self.awaiting_command = False
                else:
                    logger.info(f"✅ Command received: '{transcript}' → GUI textbox")
                    # Thread-safe GUI update
                    self.gui.after(0, lambda: self.gui.set_voice_input(transcript))
                    self.awaiting_command = False

    def on_terminated(self, client, event: TerminationEvent):
        logger.info(f"STT session terminated")

    def on_error(self, client, error: StreamingError):
        logger.error(f"STT error: {error}")

    def start(self):
        if self.running: return
        self.running = True

        client = StreamingClient(StreamingClientOptions(api_key=ASSEMBLY_API_KEY, api_host="streaming.assemblyai.com"))
        self.client = client

        client.on(StreamingEvents.Begin, self.on_begin)
        client.on(StreamingEvents.Turn, self.on_turn)
        client.on(StreamingEvents.Termination, self.on_terminated)
        client.on(StreamingEvents.Error, self.on_error)

        client.connect(StreamingParameters(
            sample_rate=16000,
            format_turns=True,
            end_of_turn_confidence_threshold=0.5,
            min_end_of_turn_silence_when_confident=100,
            max_turn_silence=1000,
            language="en",
        ))

        def stream_thread():
            try:
                logger.info("🎤 Listening for 'hey bot' hotword...")
                client.stream(aai.extras.MicrophoneStream(sample_rate=16000))
            except Exception as e:
                logger.exception(f"STT stream error: {e}")
            finally:
                self.running = False

        self.thread = threading.Thread(target=stream_thread, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        try:
            if self.client:
                self.client.disconnect(terminate=True)
        except Exception:
            pass

# ---------------- MAIN EXECUTION ----------------
if __name__ == "__main__":
    try:
        robot = RobotController()
        root = tk.Tk()
        face = RobotFace(root, robot)

        stt = STTManager(controller=robot, gui=face)
        stt.start()
        logger.info("🚀 BotFir ready! Say 'hey bot' then your command!")

        greeting = "Hi I am bot fir speed 1 giga herts memory 1 giga byte"
        robot.speak(greeting)
        face.log("🤖 BotFir ONLINE | Say 'hey bot' → speak command → press ENTER!", "SYSTEM")

        root.mainloop()

    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Critical Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            if 'stt' in locals():
                stt.stop()
        except:
            pass
        if 'robot' in locals():
            robot.cleanup()
