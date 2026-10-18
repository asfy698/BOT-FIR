# services/gemini_client.py - Gemini API client for chat and TTS
from google import genai
from google.genai import types
import struct
import subprocess
import os
import re
import hashlib
import config


class GeminiClient:
    """Manages Gemini API interactions for chat and text-to-speech."""

    def __init__(self, api_key=None):
        api_key = api_key or config.GEMINI_API_KEY
        self.gemini_client = genai.Client(api_key=api_key)
        self.current_process = None
        self._interrupted = False

    def chat(self, prompt, language_code="en"):
        """Chat with Gemini API."""
        try:
            model = "gemini-flash-latest"
            language_name = {
                "en": "English",
                "ta": "Tamil",
                "ms": "Malay (Bahasa Melayu)",
            }.get(language_code, "the same language as the user")
            multilingual_prompt = (
                f"Reply concisely in {language_name}. "
                f"Do not translate unless asked. User: {prompt}"
            )
            response = self.gemini_client.models.generate_content(
                model=model, contents=multilingual_prompt
            )
            return response.text
        except Exception as e:
            print(f"Gemini Chat Error: {e}")
            return "I am having trouble connecting to my brain."

    def _convert_to_wav(self, audio_data: bytes, mime_type: str) -> bytes:
        """Convert raw audio data to WAV format."""
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

    def _get_cache_filename(self, text):
        """Generates a standardized filename for caching."""
        # Replace non-alphanumeric chars with underscore
        clean_text = re.sub(r'[^a-zA-Z0-9]', '_', text)
        # Collapse multiple underscores
        clean_text = re.sub(r'_+', '_', clean_text)
        # Strip underscores from ends
        clean_text = clean_text.strip('_')
        # Limit length
        # Tamil text may have no ASCII characters, so include a stable digest.
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
        clean_text = clean_text[:40] or "speech"
        filename = f"{clean_text}_{digest}.wav"
        return filename

    def _play_audio_file(self, file_path):
        """Play audio using aplay with immediate interrupt support."""
        if getattr(self, "_interrupted", False):
            return
        try:
            self.current_process = subprocess.Popen(["aplay", file_path])
            self.current_process.wait()
        except Exception as e:
            print(f"WARNING: Could not play audio: {e}")
        finally:
            self.current_process = None

    def stop_speaking(self):
        """Immediately terminate any active speech playback."""
        self._interrupted = True
        proc = getattr(self, "current_process", None)
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=0.2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        try:
            subprocess.run(["pkill", "-9", "aplay"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        self.current_process = None

    def speak(self, text):
        """Generate and play text-to-speech audio with caching."""
        print(f"TTS Request: {text}")
        self._interrupted = False

        # 1. Check Cache with standardized filename
        filename = self._get_cache_filename(text)
        cache_path = os.path.join(config.TTS_CACHE_DIR, filename)

        if os.path.exists(cache_path):
            print(f"✓ Playing from cache: {cache_path}")
            self._play_audio_file(cache_path)
            return

        if self._interrupted:
            return

        # 2. Generate if not in cache
        print("Generating new audio via Gemini API...")
        model = "gemini-2.5-flash-preview-tts"
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=text)])]

        tts_config = types.GenerateContentConfig(
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
            chunk_count = 0

            for chunk in self.gemini_client.models.generate_content_stream(
                model=model, contents=contents, config=tts_config
            ):
                if self._interrupted:
                    print("TTS generation cancelled due to interrupt.")
                    return
                chunk_count += 1
                if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                    part = chunk.candidates[0].content.parts[0]
                    if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.data:
                        data_buffer += part.inline_data.data
                        mime = part.inline_data.mime_type

            if not data_buffer or self._interrupted:
                if not data_buffer:
                    print("ERROR: Empty audio buffer from API")
                return

            wav = self._convert_to_wav(data_buffer, mime)

            # Save to cache
            with open(cache_path, "wb") as f:
                f.write(wav)
            print(f"✓ Audio cached to: {cache_path}")

            # Play
            self._play_audio_file(cache_path)

        except Exception as e:
            print(f"TTS Error: {e}")
            import traceback
            traceback.print_exc()

