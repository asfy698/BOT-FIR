from vosk import Model, KaldiRecognizer
import pyaudio as sd
import json

model = Model("/home/asfirnazyasin/airobot/vosk-model-small-en-us-0.15")
rec = KaldiRecognizer(model, 16000)

def callback(indata, frames, time, status):
    if rec.AcceptWaveform(indata):
        print(json.loads(rec.Result()))
    else:
        print(json.loads(rec.PartialResult()))

with id.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                       channels=1, callback=callback):
    print("Speak now...")
    while True:
        pass
