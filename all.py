try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# robot_main.py - Unified Robot Control Script

# --- 1. RASPBERRY PI HARDWARE & MOTOR CONTROL IMPORTS ---
import RPi.GPIO as GPIO
import time
import subprocess  # For playing audio

# --- 2. CAMERA IMPORTS ---
from picamera2 import Picamera2
import os

# --- 3. OBJECT DETECTION (HUGGING FACE) IMPORTS ---
import requests
import base64
import mimetypes

# --- 4. TEXT-TO-SPEECH (GEMINI API) IMPORTS ---
from google import genai
from google.genai import types
import struct
import shutil  # Used for cleanup check

# --- 5. GUI (FACE) IMPORTS ---
import tkinter as tk
from PIL import Image, ImageTk

# --- CONFIGURATION ---
# Gemini API Keys (toggle if rate limit reached)
# GEMINI_API_KEY configured via .env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# GEMINI_API_KEY configured via .env
# GEMINI_API_KEY configured via .env

HF_API_KEY = os.getenv("HF_API_KEY", "")
HF_API_URL = "https://router.huggingface.co/v1/chat/completions"
IMAGE_FILE_NAME = "captured_image.jpg"
AUDIO_FILE_NAME = "tts_output.wav"


class RobotController:
    """Manages all hardware and API interactions for the robot."""

    # Motor Pin Definitions (BCM Numbering)
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
        self.picam2 = None  # Initialize camera later

    # --- MOTOR CONTROL FUNCTIONS ---
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

    # --- CAMERA FUNCTIONS ---
    def take_picture(self):
        if self.picam2 is None:
            try:
                self.picam2 = Picamera2()
            except RuntimeError as e:
                print(f"ERROR: Failed to initialize camera. {e}")
                return False

        try:
            config = self.picam2.create_still_configuration(
                main={"size": (1920, 1080)}
            )
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
        if not self.take_picture():
            return "Could not capture image."

        data_uri = self.get_image_data_uri(IMAGE_FILE_NAME)
        if not data_uri:
            return "Could not read image."

        payload = {
            "model": "zai-org/GLM-4.5V:novita",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this scene in one short sentence."},
                        {"type": "image_url", "image_url": {"url": data_uri}},
                    ],
                }
            ],
            "max_tokens": 100,
        }
        headers = {"Authorization": f"Bearer {HF_API_KEY}", "Content-Type": "application/json"}

        try:
            r = requests.post(HF_API_URL, headers=headers, json=payload, timeout=20)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Object detection error: {e}"

    # --- TEXT TO SPEECH ---
    def _convert_to_wav(self, audio_data: bytes, mime_type: str) -> bytes:
        bits_per_sample = 16
        sample_rate = 24000
        num_channels = 1
        data_size = len(audio_data)
        block_align = num_channels * (bits_per_sample // 8)
        byte_rate = sample_rate * block_align
        chunk_size = 36 + data_size

        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", chunk_size, b"WAVE", b"fmt ", 16, 1,
            num_channels, sample_rate, byte_rate,
            block_align, bits_per_sample, b"data", data_size
        )
        return header + audio_data

    def speak(self, text):
        print(f"TTS: {text}")

        model = "gemini-2.5-flash-preview-tts"
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=text)])]

        config = types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Umbriel"
                    )
                )
            )
        )

        try:
            data_buffer = b""
            mime = "audio/L16;rate=24000"

            for chunk in self.gemini_client.models.generate_content_stream(
                model=model, contents=contents, config=config
            ):
                # Fix: Access parts array, not content directly
                if (chunk.candidates is None or 
                    chunk.candidates[0].content is None or 
                    chunk.candidates[0].content.parts is None):
                    continue
                
                part = chunk.candidates[0].content.parts[0]
                if part.inline_data and part.inline_data.data:
                    data_buffer += part.inline_data.data
                    mime = part.inline_data.mime_type

            if not data_buffer:
                print("ERROR: Empty audio.")
                return

            wav = self._convert_to_wav(data_buffer, mime)
            with open(AUDIO_FILE_NAME, "wb") as f:
                f.write(wav)

            try:
                subprocess.run(["aplay", AUDIO_FILE_NAME])
            except:
                pass

        except Exception as e:
            print("TTS Error:", e)

    # --- CLEANUP ---
    def cleanup(self):
        print("Cleaning up...")
        self.motors_stop()
        GPIO.cleanup()
        if os.path.exists(IMAGE_FILE_NAME):
            os.remove(IMAGE_FILE_NAME)
        if os.path.exists(AUDIO_FILE_NAME):
            os.remove(AUDIO_FILE_NAME)
        print("Done.")


class RobotFace(tk.Frame):
    def __init__(self, master, controller):
        tk.Frame.__init__(self, master)
        self.controller = controller
        self.master = master

        master.title("BotFir Control Panel")
        master.attributes("-fullscreen", True)
        master.config(bg="#ECE9D8")  # Windows XP Luna background
        master.configure(cursor="none")

        # Get screen dimensions
        screen_width = master.winfo_screenwidth()
        screen_height = master.winfo_screenheight()
        
        # ---- WINDOWS XP INSPIRED SIZING ----
        face_size = min(int(screen_width * 0.35), 260)
        FACE_SIZE = (face_size, face_size)
        
        title_font_size = max(int(screen_height * 0.06), 28)
        input_font_size = max(int(screen_height * 0.035), 14)
        status_font_size = max(int(screen_height * 0.03), 12)
        button_font_size = max(int(screen_height * 0.028), 11)

        try:
            self.mouth_closed = ImageTk.PhotoImage(
                Image.open("face_closed.png").resize(FACE_SIZE, Image.Resampling.LANCZOS)
            )
            self.mouth_open = ImageTk.PhotoImage(
                Image.open("face_open.png").resize(FACE_SIZE, Image.Resampling.LANCZOS)
            )
        except:
            self.mouth_closed = None
            self.mouth_open = None

        # Main container - Windows XP style
        main_frame = tk.Frame(master, bg="#ECE9D8", relief="flat")
        main_frame.pack(fill="both", expand=True, padx=8, pady=8)

        # Title bar - XP style gradient
        title_frame = tk.Frame(main_frame, bg="#0054E3", height=30, relief="raised", bd=1)
        title_frame.pack(fill="x", pady=(0, 5))
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame, text="🤖 BotFir Control Center", 
            bg="#0054E3", fg="white", 
            font=("Tahoma", max(int(status_font_size * 1.2), 13), "bold"),
            anchor="w", padx=10
        )
        title_label.pack(fill="both", expand=True)

        # Face panel - XP groupbox style
        face_panel = tk.Frame(main_frame, bg="white", relief="groove", bd=2)
        face_panel.pack(pady=3)
        
        self.face_label = tk.Label(face_panel, bg="white", borderwidth=0)
        if self.mouth_closed:
            self.face_label.config(image=self.mouth_closed)
        else:
            self.face_label.config(text="🤖", fg="#003399", font=("Arial", title_font_size))
        self.face_label.pack(padx=10, pady=10)

        # Status panel - XP info box
        status_frame = tk.Frame(main_frame, bg="white", relief="sunken", bd=1)
        status_frame.pack(fill="x", pady=3, padx=5)
        
        self.status = tk.Label(
            status_frame, text="Ready", bg="white", fg="#006600", 
            font=("Tahoma", status_font_size, "bold"),
            wraplength=screen_width - 40, pady=4
        )
        self.status.pack()

        # Input panel - XP textbox
        input_panel = tk.LabelFrame(
            main_frame, text=" Command Input ", 
            bg="#ECE9D8", fg="#003399",
            font=("Tahoma", status_font_size - 1, "bold"),
            relief="groove", bd=2, padx=5, pady=5
        )
        input_panel.pack(fill="x", pady=5, padx=5)
        
        self.command_input = tk.Entry(
            input_panel, 
            bg="white", 
            fg="black", 
            font=("Tahoma", input_font_size),
            insertbackground="black",
            relief="sunken",
            bd=2,
            highlightthickness=0
        )
        self.command_input.pack(fill="x", ipady=4)
        self.command_input.bind("<Return>", self.handle_command)
        self.command_input.focus_set()

        # Control panel - XP button group
        control_panel = tk.LabelFrame(
            main_frame, text=" Quick Controls ", 
            bg="#ECE9D8", fg="#003399",
            font=("Tahoma", status_font_size - 1, "bold"),
            relief="groove", bd=2, padx=8, pady=5
        )
        control_panel.pack(pady=5)
        
        btn_style = {
            "font": ("Tahoma", button_font_size, "bold"),
            "relief": "raised",
            "bd": 2,
            "padx": 10,
            "pady": 6,
            "width": 5,
            "cursor": "hand2",
            "activebackground": "#CCE8FF"
        }
        
        # Direction controls
        self.btn_forward = tk.Button(
            control_panel, text="▲", bg="#D4D0C8", fg="#000080",
            command=lambda: self.quick_command("forward"), **btn_style
        )
        self.btn_forward.grid(row=0, column=1, padx=3, pady=2)
        
        self.btn_left = tk.Button(
            control_panel, text="◄", bg="#D4D0C8", fg="#000080",
            command=lambda: self.quick_command("left"), **btn_style
        )
        self.btn_left.grid(row=1, column=0, padx=3, pady=2)
        
        self.btn_stop = tk.Button(
            control_panel, text="■", bg="#D4D0C8", fg="#CC0000",
            command=lambda: self.quick_command("stop"), **btn_style
        )
        self.btn_stop.grid(row=1, column=1, padx=3, pady=2)
        
        self.btn_right = tk.Button(
            control_panel, text="►", bg="#D4D0C8", fg="#000080",
            command=lambda: self.quick_command("right"), **btn_style
        )
        self.btn_right.grid(row=1, column=2, padx=3, pady=2)
        
        self.btn_backward = tk.Button(
            control_panel, text="▼", bg="#D4D0C8", fg="#000080",
            command=lambda: self.quick_command("backward"), **btn_style
        )
        self.btn_backward.grid(row=2, column=1, padx=3, pady=2)
        
        # Camera button
        self.btn_analyze = tk.Button(
            control_panel, text="📷", bg="#D4D0C8", fg="#006600",
            command=lambda: self.quick_command("analyze"),
            font=("Tahoma", button_font_size + 2), relief="raised",
            bd=2, padx=10, pady=6, width=5, cursor="hand2",
            activebackground="#CCE8FF"
        )
        self.btn_analyze.grid(row=1, column=3, padx=3, pady=2)
        
        # Store dimensions
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.button_font_size = button_font_size
        self.status_font_size = status_font_size

    def set_status(self, text, color="#006600"):
        """Update status with Windows XP colors"""
        self.status.config(text=text, fg=color)
        self.master.update()

    def quick_command(self, cmd):
        """Handle button clicks"""
        self.command_input.delete(0, tk.END)
        self.command_input.insert(0, cmd)
        self.handle_command()

    def animate_mouth(self, duration=1):
        """Animate mouth while motors run - no separate sleep needed"""
        if not self.mouth_open:
            return
        
        self.face_label.config(image=self.mouth_open)
        self.master.update()
        
        # Animate in small steps to keep UI responsive
        steps = int(duration * 10)  # 10 steps per second
        for _ in range(steps):
            time.sleep(0.1)
            self.master.update()
        
        self.face_label.config(image=self.mouth_closed)
        self.master.update()

    def display_captured_image(self):
        if os.path.exists(IMAGE_FILE_NAME):
            try:
                img = Image.open(IMAGE_FILE_NAME)
                img_width = int(self.screen_width * 0.75)
                img_height = int(self.screen_height * 0.45)
                img = img.resize((img_width, img_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.face_label.config(image=photo, bg="white")
                self.face_label.image = photo
                
                # XP style close button
                if hasattr(self, 'close_btn'):
                    self.close_btn.pack(pady=5)
                else:
                    self.close_btn = tk.Button(
                        self.master, text="✖ Close Preview", 
                        bg="#D4D0C8", fg="#CC0000", 
                        font=("Tahoma", self.button_font_size, "bold"),
                        command=self.restore_face,
                        relief="raised", bd=2, padx=15, pady=5,
                        cursor="hand2", activebackground="#CCE8FF"
                    )
                    self.close_btn.pack(pady=5)
            except Exception as e:
                print(f"Error displaying image: {e}")
    
    def restore_face(self):
        """Restore the normal robot face"""
        if self.mouth_closed:
            self.face_label.config(image=self.mouth_closed, bg="white")
            self.face_label.image = self.mouth_closed
        else:
            self.face_label.config(text="🤖", fg="#003399", font=("Arial", 64), bg="white")
        
        if hasattr(self, 'close_btn'):
            self.close_btn.pack_forget()
        
        self.set_status("Ready", "#006600")

    def handle_command(self, event=None):
        cmd = self.command_input.get().lower().strip()
        if not cmd:
            return
            
        self.command_input.delete(0, tk.END)
        self.set_status(f"Processing: {cmd}...", "#0054E3")

        if "forward" in cmd or "▲" in cmd:
            self.controller.motors_forward()
            self.animate_mouth(2.5)  # Motor runs for 2.5 seconds
            self.controller.motors_stop()
            self.set_status("✓ Moved Forward", "#006600")

        elif "backward" in cmd or "▼" in cmd:
            self.controller.motors_backward()
            self.animate_mouth(2.5)  # Motor runs for 2.5 seconds
            self.controller.motors_stop()
            self.set_status("✓ Moved Backward", "#006600")

        elif "left" in cmd or "◄" in cmd:
            self.controller.motors_turning_L()
            self.animate_mouth(1.0)  # Motor runs for 1 second
            self.controller.motors_stop()
            self.set_status("✓ Turned Left", "#006600")

        elif "right" in cmd or "►" in cmd:
            self.controller.motors_turning_R()
            self.animate_mouth(1.0)  # Motor runs for 1 second
            self.controller.motors_stop()
            self.set_status("✓ Turned Right", "#006600")

        elif "stop" in cmd or "■" in cmd:
            self.controller.motors_stop()
            self.set_status("■ Stopped", "#CC0000")

        elif "capture" in cmd or "snapshot" in cmd:
            self.set_status("📸 Capturing Image...", "#FF8C00")
            self.controller.take_picture()
            self.set_status("✓ Image Captured", "#006600")

        elif "analyze" in cmd or "what is this" in cmd or "📷" in cmd:
            self.set_status("🔍 Analyzing Scene...", "#9900CC")
            self.animate_mouth(0.5)
            text = self.controller.detect_objects()
            self.animate_mouth(1.0)
            self.display_captured_image()
            
            # Truncate long text for display
            display_text = text[:60] + "..." if len(text) > 60 else text
            self.set_status(display_text, "#000080")
            self.controller.speak(text)

        elif "exit" in cmd or "quit" in cmd:
            self.set_status("👋 Shutting Down...", "#CC0000")
            self.master.after(1000, self.master.quit)

        else:
            self.set_status(f"❌ Unknown: {cmd}", "#CC6600")
            self.controller.speak("Command not recognized.")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    robot = None
    try:
        robot = RobotController()

        root = tk.Tk()
        face = RobotFace(root, robot)

        greeting = "Hi, I am BotFir. Speed 1.2 giga herts memory 64 giga byte."
        robot.speak(greeting)
        face.set_status("System Ready", "#006600")

        root.mainloop()

    except KeyboardInterrupt:
        print("Interrupted.")

    except Exception as e:
        print("Error:", e)

    finally:
        if robot:
            robot.cleanup()
        print("Program finished.")
