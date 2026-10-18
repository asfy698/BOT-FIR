try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# To run this code you need to install the following dependencies:
# pip install google-genai
# NO extra audio libraries needed, this uses the built-in 'subprocess'.

import mimetypes
import os
import struct
import subprocess # 🌟 NEW: Added for system command execution
from google import genai
from google.genai import types


# ⚠️ SECURITY WARNING: 
# Replace the placeholder with your actual API key. 
# -----------------------------------------------------------
API_KEY = os.getenv("GEMINI_API_KEY", "")
# -----------------------------------------------------------


def save_binary_file(file_name, data):
    """Writes the binary audio data to a file."""
    try:
        with open(file_name, "wb") as f:
            f.write(data)
        print(f"File saved successfully to: {file_name}")
        return True # Return success status
    except IOError as e:
        print(f"Error saving file {file_name}: {e}")
        return False # Return failure status

# 🌟 NEW FUNCTION: Plays the saved audio file
def play_audio(file_path):
    """Plays the audio file using the system's default player."""
    if os.name == 'nt':  # Windows
        # Use 'start' command to open the file with the default program
        subprocess.run(['start', file_path], shell=True, check=True)
    elif os.name == 'posix': # macOS or Linux
        # Use 'open' (macOS) or 'xdg-open' (most Linux)
        try:
            subprocess.run(['xdg-open', file_path], check=True) # Linux
        except FileNotFoundError:
            try:
                subprocess.run(['open', file_path], check=True) # macOS
            except FileNotFoundError:
                print("Could not find 'xdg-open' or 'open'. Please open the file manually.")
    else:
        print(f"Unsupported OS for automatic playback. Please open '{file_path}' manually.")
    print(f"Attempting to play audio file: {file_path}")


def generate():
    """Generates the speech, saves it, and attempts to play it."""
    if not API_KEY or not API_KEY:
        print("ERROR: Please replace the placeholder API_KEY with your actual Gemini API key.")
        return

    client = genai.Client(
        api_key=API_KEY, 
    )

    model = "gemini-2.5-flash-preview-tts"
    
    input_text = """Assalamu Alaikum:
my maker Firnaz Yasin, handsome Sree Kanth Sir, beautiful Principal Mam"""
    
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=input_text),
            ],
        ),
    ]
    
    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        response_modalities=[
            "audio",
        ],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name="Zubenelgenubi"
                )
            )
        ),
    )

    file_index = 0
    generated_file_path = None # To store the path of the saved file
    print(f"Generating speech for the text: '{input_text}'")
    
    try:
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if (
                chunk.candidates is None
                or chunk.candidates[0].content is None
                or chunk.candidates[0].content.parts is None
            ):
                continue
            
            part = chunk.candidates[0].content.parts[0]
            if part.inline_data and part.inline_data.data:
                # We'll save the file using a fixed name for simplicity, assuming a single output chunk
                file_name = f"tts_output_{file_index}"
                inline_data = part.inline_data
                data_buffer = inline_data.data
                file_extension = mimetypes.guess_extension(inline_data.mime_type)
                
                if file_extension is None:
                    file_extension = ".wav"
                    data_buffer = convert_to_wav(inline_data.data, inline_data.mime_type)
                
                # Construct the full path
                generated_file_path = f"{file_name}{file_extension}"
                
                # Save the file
                if save_binary_file(generated_file_path, data_buffer):
                    file_index += 1
                
            else:
                print(chunk.text)
        
        # 3. Play the audio file after generation is complete
        if generated_file_path:
            play_audio(generated_file_path)
        
    except Exception as e:
        print(f"\nAn API or stream error occurred: {e}")
        print("Please check your API key, model name, and network connection.")


def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """
    Generates a WAV file header for the given raw audio data.
    """
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1 
    data_size = len(audio_data)
    
    if bits_per_sample is None or sample_rate is None:
        raise ValueError("Cannot convert to WAV: Missing bits_per_sample or sample rate from MIME type.")

    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size  

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",           # ChunkID
        chunk_size,       # ChunkSize 
        b"WAVE",           # Format
        b"fmt ",           # Subchunk1ID
        16,               # Subchunk1Size 
        1,                # AudioFormat 
        num_channels,     # NumChannels
        sample_rate,      # SampleRate
        byte_rate,        # ByteRate
        block_align,      # BlockAlign
        bits_per_sample,  # BitsPerSample
        b"data",           # Subchunk2ID
        data_size         # Subchunk2Size 
    )
    return header + audio_data

def parse_audio_mime_type(mime_type: str) -> dict[str, int | None]:
    """
    Parses bits per sample and rate from an audio MIME type string.
    """
    bits_per_sample = 16
    rate = 24000

    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate_str = param.split("=", 1)[1]
                rate = int(rate_str)
            except (ValueError, IndexError):
                pass 
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass 

    return {"bits_per_sample": bits_per_sample, "rate": rate}


if __name__ == "__main__":
    generate()