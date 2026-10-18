# gui/robot_face.py - Tkinter GUI interface
import tkinter as tk
from tkinter import ttk, scrolledtext
from PIL import Image, ImageTk
import datetime
import time
import os
import config


class RobotFace(tk.Frame):
    def __init__(self, master, controller):
        tk.Frame.__init__(self, master)
        self.controller = controller
        self.master = master

        # --- THEME: "Industrial Amber" ---
        self.colors = {
            "bg": "#F2F0EB",          # Industrial Cream
            "header": "#1F1F1F",      # Dark Matte Header
            "card": "#FFFFFF",        # Clean White Cards
            "accent": "#FFB300",      # Safety Amber/Gold
            "text_dark": "#212121",   # Near Black
            "text_light": "#757575",  # Industrial Grey
            "terminal_bg": "#121212", # Console Black
            "terminal_fg": "#00E676", # Matrix Green
            "danger": "#D32F2F"       # Safety Red
        }

        master.title("BotFir AI - Production Dashboard")
        master.geometry("800x480")
        master.config(bg=self.colors["bg"])

        # Get screen dimensions
        screen_width = master.winfo_screenwidth()
        screen_height = master.winfo_screenheight()
        
        # ---- RESPONSIVE SIZING ----
        is_small_screen = screen_width < 800 or screen_height < 600
        
        if is_small_screen:
            face_size = min(int(screen_height * 0.3), 120)
            title_font = ("Helvetica", 12, "bold")
            header_height = 35
            pad_small = 2
            pad_med = 5
            btn_font = ("Helvetica", 9, "bold")
            log_height = 6
        else:
            face_size = min(int(screen_width * 0.3), 220)
            title_font = ("Helvetica", 16, "bold")
            header_height = 50
            pad_small = 5
            pad_med = 10
            btn_font = ("Helvetica", 12, "bold")
            log_height = 10
            
        FACE_SIZE = (face_size, face_size)
        self.screen_width = screen_width
        self.screen_height = screen_height

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

        # --- LAYOUT STRUCTURE ---
        # 1. Header Bar
        header = tk.Frame(master, bg=self.colors["header"], height=header_height)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        
        tk.Label(header, text="BOTFIR AI", fg=self.colors["accent"], bg=self.colors["header"], 
                 font=title_font).pack(side="left", padx=pad_med)
        tk.Label(header, text="| PRODUCTION SYSTEM v2.0", fg="#888", bg=self.colors["header"], 
                 font=("Helvetica", 10)).pack(side="left")
        
        self.status_indicator = tk.Label(header, text="● ONLINE", fg=self.colors["terminal_fg"], 
                                        bg=self.colors["header"], font=("Helvetica", 10, "bold"))
        self.status_indicator.pack(side="right", padx=pad_med)

        # 2. Main Dashboard Area
        dashboard = tk.Frame(master, bg=self.colors["bg"])
        dashboard.pack(fill="both", expand=True, padx=pad_med, pady=pad_med)

        # Left Column: Visuals & Telemetry
        left_col = tk.Frame(dashboard, bg=self.colors["bg"], width=int(screen_width*0.4))
        left_col.pack(side="left", fill="both", expand=True, padx=(0, pad_small))
        
        # Face Card
        face_card = tk.Frame(left_col, bg=self.colors["card"], relief="flat", bd=1)
        face_card.pack(fill="both", expand=True, pady=(0, pad_small))
        
        self.face_label = tk.Label(face_card, bg=self.colors["card"])
        if self.mouth_closed:
            self.face_label.config(image=self.mouth_closed)
        else:
            self.face_label.config(text="[VISUAL SYSTEM]", fg=self.colors["accent"])
        self.face_label.pack(expand=True)

        # Telemetry Card
        telemetry_card = tk.Frame(left_col, bg=self.colors["card"], height=100)
        telemetry_card.pack(fill="x")
        
        t_grid = tk.Frame(telemetry_card, bg=self.colors["card"])
        t_grid.pack(fill="both", padx=pad_med, pady=pad_med)
        
        def add_stat(parent, label, value, row, col):
            tk.Label(parent, text=label, fg=self.colors["text_light"], bg=self.colors["card"], 
                     font=("Helvetica", 8)).grid(row=row, column=col, sticky="w")
            tk.Label(parent, text=value, fg=self.colors["text_dark"], bg=self.colors["card"], 
                     font=("Helvetica", 10, "bold")).grid(row=row+1, column=col, sticky="w", padx=(0, 15))

        add_stat(t_grid, "CPU SPEED", "1.0 GHz", 0, 0)
        add_stat(t_grid, "MEMORY", "1.0 GB", 0, 1)
        add_stat(t_grid, "MOTOR STATUS", "STANDBY", 0, 2)

        # Right Column: Logs & Controls
        right_col = tk.Frame(dashboard, bg=self.colors["bg"])
        right_col.pack(side="right", fill="both", expand=True, padx=(pad_small, 0))

        # Terminal Log (Top of Right)
        log_frame = tk.Frame(right_col, bg=self.colors["terminal_bg"], relief="sunken", bd=1)
        log_frame.pack(fill="both", expand=True, pady=(0, pad_small))
        
        tk.Label(log_frame, text="SYSTEM LOGS >_", fg=self.colors["accent"], bg=self.colors["terminal_bg"], 
                 font=("Courier", 8), anchor="w").pack(fill="x", padx=2)
        
        self.log_display = scrolledtext.ScrolledText(log_frame, bg=self.colors["terminal_bg"], 
                                                    fg=self.colors["terminal_fg"], font=("Courier", 9),
                                                    height=log_height, state="disabled", relief="flat")
        self.log_display.pack(fill="both", expand=True, padx=2, pady=2)

        # Input Area
        input_frame = tk.Frame(right_col, bg=self.colors["card"], height=40)
        input_frame.pack(fill="x", pady=(0, pad_small))
        
        self.command_input = tk.Entry(input_frame, bg=self.colors["card"], fg=self.colors["text_dark"],
                                     font=("Helvetica", 12), relief="flat")
        self.command_input.pack(fill="both", expand=True, padx=pad_med, pady=5)
        self.command_input.bind("<Return>", self.handle_command)
        
        # Control Pad (Bottom of Right)
        control_pad = tk.Frame(right_col, bg=self.colors["bg"])
        control_pad.pack(fill="x")
        
        # Grid layout for controls
        for i in range(3): control_pad.columnconfigure(i, weight=1)
        
        btn_style = {
            "font": btn_font, "relief": "flat", "bd": 0, "cursor": "hand2",
            "bg": self.colors["card"], "fg": self.colors["text_dark"],
            "activebackground": self.colors["accent"], "activeforeground": "black"
        }

        # Row 1
        tk.Button(control_pad, text="▲", command=lambda: self.quick_command("forward"), **btn_style).grid(row=0, column=1, sticky="ew", padx=1, pady=1, ipady=5)
        
        # Row 2
        tk.Button(control_pad, text="◄", command=lambda: self.quick_command("left"), **btn_style).grid(row=1, column=0, sticky="ew", padx=1, pady=1, ipady=5)
        tk.Button(control_pad, text="STOP", command=lambda: self.quick_command("stop"), 
                  font=btn_font, relief="flat", bg=self.colors["danger"], fg="white", 
                  activebackground="#B71C1C", activeforeground="white").grid(row=1, column=1, sticky="ew", padx=1, pady=1, ipady=5)
        tk.Button(control_pad, text="►", command=lambda: self.quick_command("right"), **btn_style).grid(row=1, column=2, sticky="ew", padx=1, pady=1, ipady=5)
        
        # Row 3
        tk.Button(control_pad, text="▼", command=lambda: self.quick_command("backward"), **btn_style).grid(row=2, column=1, sticky="ew", padx=1, pady=1, ipady=5)
        tk.Button(control_pad, text="SCAN", command=lambda: self.quick_command("analyze"), 
                  font=btn_font, relief="flat", bg=self.colors["accent"], fg="black").grid(row=2, column=2, sticky="ew", padx=1, pady=1, ipady=5)

    def log(self, message, tag="INFO"):
        """Add message to the terminal log"""
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
        time.sleep(duration) # Simple sleep is fine for short bursts
        self.face_label.config(image=self.mouth_closed)
        self.master.update()

    def display_captured_image(self):
        if os.path.exists(config.IMAGE_FILE_NAME):
            try:
                img = Image.open(config.IMAGE_FILE_NAME)
                # Fit to face card area
                w = int(self.screen_width * 0.35)
                h = int(self.screen_height * 0.35)
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
        if not cmd: return
        
        self.command_input.delete(0, tk.END)
        self.log(f"Command: {cmd}", "USER")
        
        # Motor Commands
        if any(x in cmd for x in ["stop", "halt", "brake", "■"]):
            self.controller.motors_stop()
            self.log("Motors STOPPED", "MOTOR")
            
        elif any(x in cmd for x in ["forward", "front", "go", "up", "▲"]):
            self.controller.motors_forward()
            self.log("Moving FORWARD", "MOTOR")
            self.animate_mouth(4)
            self.controller.motors_stop()
            
        elif any(x in cmd for x in ["backward", "back", "reverse", "down", "▼"]):
            self.controller.motors_backward()
            self.log("Moving BACKWARD", "MOTOR")
            self.animate_mouth(4)
            self.controller.motors_stop()
            
        elif any(x in cmd for x in ["left", "turn left", "◄"]):
            self.controller.motors_turning_L()
            self.log("Turning LEFT", "MOTOR")
            self.animate_mouth(1.0)
            self.controller.motors_stop()
            
        elif any(x in cmd for x in ["right", "turn right", "►"]):
            self.controller.motors_turning_R()
            self.log("Turning RIGHT", "MOTOR")
            self.animate_mouth(1.0)
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
                # Restore face after a delay
                self.master.after(5000, self.restore_face)
            else:
                self.log("Camera Capture Failed", "ERROR")
                self.controller.speak("I could not capture an image.")
                
        elif any(x in cmd for x in ["exit", "quit", "shutdown"]):
            self.log("Shutdown Sequence Initiated...", "SYSTEM")
            self.master.after(1000, self.master.destroy)
            
        else:
            # Chat
            self.log("Processing Query...", "AI")
            try:
                response = self.controller.chat_with_gemini(cmd)
                self.log(f"Response: {response}", "GEMINI")
                # self.controller.speak(response) # Silent mode
            except Exception as e:
                self.log(f"API Error: {e}", "ERROR")
                self.controller.speak("I encountered an error.")

