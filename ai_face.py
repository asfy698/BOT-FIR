import tkinter as tk
from PIL import Image, ImageTk
import time, os

# GUI window
root = tk.Tk()
root.title("AI Face")
root.attributes('-fullscreen', True)  # full screen for HDMI display

# Load images (you can replace with your own PNGs)
mouth_closed = ImageTk.PhotoImage(Image.open("face_closed.png"))
mouth_open = ImageTk.PhotoImage(Image.open("face_open.png"))

label = tk.Label(root, image=mouth_closed, bg="black")
label.pack(expand=True)

def talk(text):
    os.system(f"espeak -s 160 '{text}' &")  # speak asynchronously
    for _ in range(10):
        label.config(image=mouth_open)
        root.update()
        time.sleep(0.1)
        label.config(image=mouth_closed)
        root.update()
        time.sleep(0.1)

talk("Hello, I am your AI robot!")
root.mainloop()
