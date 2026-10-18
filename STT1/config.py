try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# config.py - Configuration constants and settings
import os
import logging

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
HF_API_KEY = os.getenv("HF_API_KEY", "")
HF_API_URL = "https://router.huggingface.co/v1/chat/completions"
ASSEMBLY_API_KEY = os.getenv("ASSEMBLY_API_KEY", "")

# File paths and directories
IMAGE_FILE_NAME = "captured_image.jpg"
TTS_CACHE_DIR = "tts_cache"

# Ensure cache directory exists
os.makedirs(TTS_CACHE_DIR, exist_ok=True)

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("robot_main")

