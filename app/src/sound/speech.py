"""
sound/speech.py — Text-to-speech via Piper TTS.

The voice model is loaded when this module is imported. Audio is played
through sounddevice (same stack as DtmfPlayer) rather than aplay.

    from sound.speech import speak
    speak("Hello")
"""

import io
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
from piper import PiperVoice

_MODEL_PATH = Path(__file__).parent / "voices" / "en_US-lessac-medium.onnx"

print(f"Loading voice model: {_MODEL_PATH}")
_voice = PiperVoice.load(str(_MODEL_PATH))
print("Voice model loaded.")


def speak(text: str) -> None:
    """Synthesize *text* to speech and play it, blocking until done."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        _voice.synthesize_wav(text, wav_file)

    buf.seek(0)
    with wave.open(buf, "rb") as wav_file:
        sample_rate  = wav_file.getframerate()
        n_frames     = wav_file.getnframes()
        raw          = wav_file.readframes(n_frames)

    # Piper outputs 16-bit PCM mono; convert to float32 in [-1.0, 1.0]
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

    sd.play(samples, samplerate=sample_rate)


def stop() -> None:
    """Stop any currently playing speech immediately."""
    sd.stop()
