try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import os
import requests
import base64
import mimetypes

# REPLACE THIS with your NEW, uncompromised key
HF_API_KEY = os.getenv("HF_API_KEY", "")

API_URL = "https://router.huggingface.co/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {HF_API_KEY}",
    "Content-Type": "application/json"
}

def get_image_data_uri(image_path):
    """Converts local file to Data URI."""
    if not os.path.exists(image_path):
        print(f"Skipping missing file: {image_path}")
        return None
        
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = 'image/jpeg'

    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        return f"data:{mime_type};base64,{encoded_string}"

def analyze_multiple_images(image_paths):
    # 1. Prepare the content list with the text prompt first
    content_list = [
        {
            "type": "text",
            "text": "I am providing multiple images. For EACH image, list the unique objects present as a Python list. Format the output as:\nImage 1: ['obj1', 'obj2']\nImage 2: ['obj1', 'obj2']..."
        }
    ]

    # 2. Loop through paths and add each image to the content list
    for path in image_paths:
        data_uri = get_image_data_uri(path)
        if data_uri:
            content_list.append({
                "type": "image_url",
                "image_url": {"url": data_uri}
            })

    # 3. Construct the payload
    payload = {
        "model": "zai-org/GLM-4.5V:novita",
        "messages": [
            {
                "role": "user",
                "content": content_list
            }
        ],
        "max_tokens": 1000  # Increased tokens since we have 3 images
    }
    
    # 4. Send the single request
    try:
        print("Sending 1 request with all images... please wait.")
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

# --- MAIN ---
image_paths = [
    r"./test_image.jpg"
]

result = analyze_multiple_images(image_paths)

if result and "choices" in result:
    print("\n--- Combined Result ---")
    print(result["choices"][0]["message"]["content"])
else:
    print("Failed to get result.")
