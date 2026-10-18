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
import config


class STTManager:
    """Runs AssemblyAI streaming in a background thread and pushes final turns to a queue.
       Implements wake-word behavior Option 2:
         - Detect "hey bot" (hotword)
         - Say "Yes fir?"
         - The next user turn (end_of_turn) is treated as the actual command
    """

    def __init__(self, controller, gui=None):
        self.controller = controller
        self.gui = gui
        self.queue = queue.Queue()
        self.awaiting_command = False
        self.awaiting_since = None
        self.timeout_seconds = 6  # time to wait for follow-up command after wake word
        self.running = False
        self.client = None
        self.thread = None

        # set assemblyai key
        aai.settings.api_key = config.ASSEMBLY_API_KEY

    # event handlers
    def on_begin(self, client, event: BeginEvent):
        config.logger.info(f"STT session started: {event.id}")

    def on_turn(self, client, event: TurnEvent):
        # only push final/complete turns (end_of_turn)
        if event.end_of_turn:
            transcript = event.transcript or ""
            # push to queue for processing
            self.queue.put(transcript)
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

    def command_processor_loop(self):
        """Runs in a separate thread to process transcripts and map to robot actions."""
        config.logger.info("STT command processor started.")
        while self.running:
            try:
                # timeout so we can check running flag
                transcript = self.queue.get(timeout=3.0)
            except queue.Empty:
                # check awaiting_command timeout
                if self.awaiting_command and (time.time() - self.awaiting_since) > self.timeout_seconds:
                    config.logger.info("Awaiting command timed out.")
                    self.awaiting_command = False
                continue

            t = transcript.lower().strip()
            config.logger.info(f"Received transcript: {t}")

            # If not currently awaiting command: check for hotword
            if not self.awaiting_command:
                if "hello" in t or "Hello" in t:
                    config.logger.info("Hotword detected. Awaiting follow-up command.")
                    # ask via TTS
                    try:
                        self.controller.speak("Yes fir?")
                    except Exception as e:
                        config.logger.warning(f"TTS failed: {e}")
                    self.awaiting_command = True
                    self.awaiting_since = time.time()
                else:
                    # not hotword — ignore (could be background speech)
                    config.logger.debug("No hotword and not awaiting command: ignored.")
                continue

            # If awaiting a command, this transcript is the user's command
            if self.awaiting_command:
                cmd = t
                self.awaiting_command = False  # reset
                config.logger.info(f"Processing voice command: {cmd}")

                # Map to robot actions
                try:
                    # Movement
                    if any(x in cmd for x in ["move forward", "forward", "go forward", "go ahead"]):
                        config.logger.info("Voice command -> MOVE FORWARD")
                        # Start moving, animate mouth, then stop
                        self.controller.motors_forward()
                        if self.gui:
                            self.gui.log("Voice: move forward", "VOICE")
                            self.gui.animate_mouth(2)
                        time.sleep(2)
                        self.controller.motors_stop()

                    elif any(x in cmd for x in ["move backward", "backward", "go back", "reverse"]):
                        config.logger.info("Voice command -> MOVE BACKWARD")
                        self.controller.motors_backward()
                        if self.gui:
                            self.gui.log("Voice: move backward", "VOICE")
                            self.gui.animate_mouth(2)
                        time.sleep(2)
                        self.controller.motors_stop()

                    # Analyze / what is this
                    elif any(x in cmd for x in ["analyze", "what is this", "what's this", "what is that"]):
                        config.logger.info("Voice command -> ANALYZE")
                        if self.gui:
                            self.gui.log("Voice: analyze", "VOICE")
                        image_path = self.controller.capture_image()
                        if image_path:
                            if self.gui:
                                self.gui.display_captured_image()
                                self.gui.log("Image captured — analyzing...", "AI")
                            description = self.controller.analyze_image(image_path)
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
                    elif any(x in cmd for x in ["stop", "halt", "brake"]):
                        config.logger.info("Voice command -> STOP")
                        self.controller.motors_stop()
                        if self.gui:
                            self.gui.log("Voice: stop", "VOICE")

                    # fallback: treat as chat query to Gemini
                    else:
                        config.logger.info("Voice command -> CHAT / fallback")
                        if self.gui:
                            self.gui.log(f"Voice query: {cmd}", "VOICE")
                        resp = self.controller.chat_with_gemini(cmd)
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
                min_end_of_turn_silence_when_confident=100,
                max_turn_silence=1000,
                language="en",
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

