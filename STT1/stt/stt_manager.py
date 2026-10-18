# stt/stt_manager.py - AssemblyAI speech-to-text manager
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
import threading
import queue
import time
import re
import config


COMMANDS = {
    "forward": [
        "move forward", "forward", "go forward", "go ahead",
        "முன்னேறு", "முன்னால் செல்", "முன்னே போ", "முன் செல்",
        "maju", "bergerak ke hadapan", "ke hadapan", "ke depan",
    ],
    "backward": [
        "move backward", "backward", "go back", "reverse",
        "பின்னேறு", "பின்னால் செல்", "பின்னே போ", "பின் செல்",
        "undur", "bergerak ke belakang", "ke belakang",
    ],
    "left": [
        "turn left", "go left", "left",
        "இடப்பக்கம் திரும்பு", "இடது பக்கம்", "இடது",
        "belok kiri", "pusing kiri", "kiri",
    ],
    "right": [
        "turn right", "go right", "right",
        "வலப்பக்கம் திரும்பு", "வலது பக்கம்", "வலது",
        "belok kanan", "pusing kanan", "kanan",
    ],
    "analyze": [
        "analyze", "what is this", "what's this", "what is that",
        "இது என்ன", "அது என்ன", "இதை பார்", "என்ன பார்க்கிறாய்",
        "analisis", "ini apa", "apakah ini", "lihat ini",
    ],
    "location": [
        "hey bot where am i", "where am i", "send current location",
        "current location", "send location", "share location",
    ],
    "stop": [
        "stop", "halt", "brake",
        "நிறுத்து", "நில்", "நிறுத்துங்கள்",
        "berhenti", "hentikan",
    ],
}

LANGUAGE_NAMES = {"en": "English", "ta": "Tamil", "ms": "Malay"}


class STTManager:
    """Runs AssemblyAI streaming and processes every completed utterance."""

    def __init__(self, controller, gui=None):
        self.controller = controller
        self.gui = gui
        self.queue = queue.Queue()
        self.running = False
        self.client = None
        self.thread = None
        self.speaking = False
        self.ignore_transcripts_until = 0.0
        self.location_callback = None
        # Let all RobotController speech temporarily mute transcript handling.
        self.controller.stt_manager = self

        # set assemblyai key
        aai.settings.api_key = config.ASSEMBLY_API_KEY

    # event handlers
    def on_begin(self, client, event: BeginEvent):
        config.logger.info(f"STT session started: {event.id}")

    @staticmethod
    def _is_stop_word(transcript: str) -> bool:
        """Check if transcript is strictly the interrupt command 'stop'."""
        if not transcript:
            return False
        cleaned = re.sub(r'[^\w\s]', '', transcript).strip().lower()
        words = cleaned.split()
        if not words:
            return False
        # Matches only when the utterance consists solely of the word 'stop'
        return all(w == 'stop' for w in words)

    def on_turn(self, client, event: TurnEvent):
        transcript = (event.transcript or "").strip()
        if not transcript and hasattr(event, "words") and event.words:
            transcript = " ".join(getattr(w, "text", "") for w in event.words).strip()

        # Interrupt check: if robot is talking and the word is 'stop', halt immediately!
        if self.speaking:
            if self._is_stop_word(transcript):
                config.logger.info(
                    f"INTERRUPT TRIGGERED: 'stop' heard while speaking ('{transcript}'). Halting speech immediately."
                )
                self.controller.stop_speaking()
                self.speaking = False
                self.ignore_transcripts_until = time.time() + 1.5
                if self.gui:
                    try:
                        self.gui.log("Interrupted: stop", "VOICE")
                    except Exception:
                        pass
                return
            else:
                config.logger.debug(
                    f"Ignoring utterance while speaking: {transcript}"
                )
                return

        # Cooldown check: ignore echo / residual audio after speaking
        if time.time() < self.ignore_transcripts_until:
            config.logger.debug(f"Ignoring cooldown transcript: {transcript}")
            return

        # Normal command processing for completed turns
        if event.end_of_turn:
            if not transcript:
                return
            # push to queue for processing
            language_code = getattr(event, "language_code", None) or ""
            language_confidence = getattr(event, "language_confidence", None)
            self.queue.put((transcript, language_code))
            if language_code:
                config.logger.info(
                    f"Detected language: {language_code} "
                    f"(confidence={language_confidence})"
                )
            config.logger.debug(f"STT on_turn queued: {transcript}")

            # If not formatted, request formatting (optional)
            if not event.turn_is_formatted:
                params = StreamingSessionParameters(format_turns=True)
                try:
                    # set params on client
                    self.client.set_params(params)
                except Exception:
                    pass

    def on_terminated(self, client, event: TerminationEvent):
        config.logger.info(f"STT session terminated: {event.audio_duration_seconds} seconds audio processed")

    def on_error(self, client, error: StreamingError):
        config.logger.error(f"STT error: {error}")

    def set_speaking(self, speaking):
        """Suppress microphone transcripts while robot audio is playing."""
        self.speaking = speaking
        if not speaking:
            # AssemblyAI final turns can arrive shortly after playback ends.
            self.ignore_transcripts_until = time.time() + 2.0

    @staticmethod
    def _guess_language(text):
        """Fallback when the streaming event has no language metadata."""
        if any("\u0b80" <= char <= "\u0bff" for char in text):
            return "ta"
        malay_markers = (
            "saya", "awak", "anda", "tolong", "maju", "undur",
            "kiri", "kanan", "berhenti", "apakah", "ini apa",
        )
        lowered = text.lower()
        if any(marker in lowered for marker in malay_markers):
            return "ms"
        return "en"

    @staticmethod
    def _matches(command, action):
        return any(phrase in command for phrase in COMMANDS[action])

    def command_processor_loop(self):
        """Runs in a separate thread to process transcripts and map to robot actions."""
        config.logger.info("STT command processor started.")
        while self.running:
            try:
                # timeout so we can check running flag
                transcript, detected_language = self.queue.get(timeout=6.0)
            except queue.Empty:
                continue

            t = transcript.lower().strip()
            config.logger.info(f"Received transcript: {t}")
            if not t:
                continue

            # Direct-listening mode: every completed utterance is a command.
            cmd = t
            language_code = (
                detected_language
                if detected_language in LANGUAGE_NAMES
                else self._guess_language(cmd)
            )

            config.logger.info(
                f"Processing voice command ({LANGUAGE_NAMES[language_code]}): {cmd}"
            )

            # Map to robot actions
            try:
                    # Movement
                    if self._matches(cmd, "forward"):
                        config.logger.info("Voice command -> MOVE FORWARD")
                        # Start moving, animate mouth, then stop
                        self.controller.motors_forward()
                        if self.gui:
                            self.gui.log("Voice: move forward", "VOICE")
                            self.gui.animate_mouth(2)
                        time.sleep(2)
                        self.controller.motors_stop()

                    elif self._matches(cmd, "backward"):
                        config.logger.info("Voice command -> MOVE BACKWARD")
                        self.controller.motors_backward()
                        if self.gui:
                            self.gui.log("Voice: move backward", "VOICE")
                            self.gui.animate_mouth(2)
                        time.sleep(2)
                        self.controller.motors_stop()

                    elif self._matches(cmd, "left"):
                        config.logger.info("Voice command -> TURN LEFT")
                        self.controller.motors_turning_L()
                        if self.gui:
                            self.gui.log("Voice: turn left", "VOICE")
                            self.gui.animate_mouth(2)
                        time.sleep(2)
                        self.controller.motors_stop()

                    elif self._matches(cmd, "right"):
                        config.logger.info("Voice command -> TURN RIGHT")
                        self.controller.motors_turning_R()
                        if self.gui:
                            self.gui.log("Voice: turn right", "VOICE")
                            self.gui.animate_mouth(2)
                        time.sleep(2)
                        self.controller.motors_stop()

                    # Analyze / what is this
                    elif self._matches(cmd, "analyze"):
                        config.logger.info("Voice command -> ANALYZE")
                        if self.gui:
                            self.gui.log("Voice: analyze", "VOICE")
                        image_path = self.controller.capture_image()
                        if image_path:
                            if self.gui:
                                self.gui.display_captured_image()
                                self.gui.log("Image captured — analyzing...", "AI")
                            description = self.controller.analyze_image(
                                image_path, language_code=language_code
                            )
                            if isinstance(description, (list, dict)):
                                # try to stringify nested structure
                                description_text = str(description)
                            else:
                                description_text = description
                            if self.gui:
                                self.gui.log(f"Analysis: {description_text}", "AI")
                            # speak via TTS
                            self.controller.speak(f"I see {description_text}")
                        else:
                            if self.gui:
                                self.gui.log("Camera capture failed", "ERROR")
                            self.controller.speak("I could not capture an image.")

                    # Stop / halt
                    elif self._matches(cmd, "stop"):
                        config.logger.info("Voice command -> STOP")
                        self.controller.motors_stop()
                        self.controller.stop_speaking()
                        if self.gui:
                            self.gui.log("Voice: stop", "VOICE")

                    # Location (Voice Trigger)
                    elif self._matches(cmd, "location") or any(p in cmd.replace(",", "").replace(".", "").replace("?", "") for p in ["hey bot where am i", "send current location", "where am i", "current location", "send location"]):
                        config.logger.info("Voice command -> SEND CURRENT LOCATION")
                        if self.gui:
                            self.gui.log("Voice: send current location", "VOICE")
                        if hasattr(self, "location_callback") and self.location_callback:
                            self.location_callback()
                        else:
                            try:
                                import current_location_send
                                current_location_send.send_location_async(
                                    status_callback=lambda msg, tag="LOCATION": self.gui.log(msg, tag) if self.gui else None
                                )
                            except Exception as loc_err:
                                config.logger.error(f"Error launching location send: {loc_err}")
                        if self.controller:
                            self.controller.speak("Sending current location")

                    # fallback: treat as chat query to Gemini
                    else:
                        config.logger.info("Voice command -> CHAT / fallback")
                        if self.gui:
                            self.gui.log(f"Voice query: {cmd}", "VOICE")
                        resp = self.controller.chat_with_gemini(
                            cmd, language_code=language_code
                        )
                        if self.gui:
                            self.gui.log(f"Gemini: {resp}", "GEMINI")
                        # optionally speak
                        try:
                            self.controller.speak(resp)
                        except Exception:
                            pass

            except Exception as e:
                config.logger.exception(f"Error handling voice command: {e}")

    def start(self):
        """Start background threads: assemblyai streaming client + command processor."""
        if self.running:
            return
        self.running = True

        # Setup client
        client = StreamingClient(
            StreamingClientOptions(
                api_key=config.ASSEMBLY_API_KEY,
                api_host="streaming.assemblyai.com",
            )
        )
        self.client = client

        # bind handlers - FIX: handlers now accept (client, event) parameters
        client.on(StreamingEvents.Begin, self.on_begin)
        client.on(StreamingEvents.Turn, self.on_turn)
        client.on(StreamingEvents.Termination, self.on_terminated)
        client.on(StreamingEvents.Error, self.on_error)

        # Connect
        client.connect(
            StreamingParameters(
                sample_rate=16000,
                format_turns=True,
                end_of_turn_confidence_threshold=0.5,
                min_end_of_turn_silence_when_confident=500,
                max_turn_silence=1600,
                speech_model="whisper-rt",
                language_detection=True,
            )
        )

        # Start command processor thread
        self.processor_thread = threading.Thread(target=self.command_processor_loop, daemon=True)
        self.processor_thread.start()

        # Start a thread that runs the streaming client (blocking)
        def client_thread_fn():
            try:
                config.logger.info("Starting AssemblyAI microphone stream...")
                client.stream(
                    aai.extras.MicrophoneStream(sample_rate=16000)
                )
            except Exception as e:
                config.logger.exception(f"AssemblyAI stream error: {e}")
            finally:
                try:
                    client.disconnect(terminate=True)
                except Exception:
                    pass
                self.running = False
                config.logger.info("AssemblyAI client thread terminating.")

        self.thread = threading.Thread(target=client_thread_fn, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        try:
            if self.client:
                self.client.disconnect(terminate=True)
        except Exception:
            pass
