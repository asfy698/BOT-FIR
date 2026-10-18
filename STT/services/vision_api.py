# services/vision_api.py - HuggingFace vision API for object detection
import os
import requests
import base64
import mimetypes
import config


class VisionAPI:
    """Manages HuggingFace vision API for object detection."""

    def __init__(self, api_key=None, api_url=None):
        self.api_key = api_key or config.HF_API_KEY
        self.api_url = api_url or config.HF_API_URL

    def get_image_data_uri(self, image_path):
        """Convert image file to data URI."""
        if not os.path.exists(image_path):
            return None
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_type = "image/jpeg"
        with open(image_path, "rb") as img:
            encoded = base64.b64encode(img.read()).decode("utf-8")
            print(encoded)  # Debug: print start of encoded string
            return f"data:{mime_type};base64,{encoded}"

    def detect_objects(self, image_path):
        """Analyze image using Hugging Face API."""
        data_uri = self.get_image_data_uri(image_path)
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
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            r = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            # adapt to assumed structure
            try:
                content = data["choices"][0]["message"]["content"]
            except Exception:
                content = str(data)
            return content
        except Exception as e:
            return f"Object detection error: {e}"

    def analyze_image(self, image_path):
        """Wrapper for detect_objects."""
        return self.detect_objects(image_path)

