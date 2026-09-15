"""
sound/speech.py — Text-to-speech via Piper TTS.

The voice model is loaded when this module is imported. Audio is played
through sounddevice (same stack as DtmfPlayer) rather than aplay.

Call precompute() with a dict of {key: text} to synthesize and cache audio
buffers at startup, then use play_precomputed(key) to play them instantly.

    from sound.speech import speak, precompute, play_precomputed
    precompute({"hello": "Hello, world!"})
    play_precomputed("hello")   # no synthesis delay
    speak("Something dynamic")  # synthesized on demand
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

# Cache of precomputed audio: key -> (samples: np.ndarray, sample_rate: int)
_cache: dict[str, tuple[np.ndarray, int]] = {}


def _synthesize(text: str) -> tuple[np.ndarray, int]:
    """Synthesize *text* and return (float32 samples, sample_rate)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        _voice.synthesize_wav(text, wav_file)
    buf.seek(0)
    with wave.open(buf, "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        raw = wav_file.readframes(wav_file.getnframes())
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return samples, sample_rate


def precompute(messages: dict[str, str]) -> None:
    """Synthesize each text in *messages* and cache it under its key.

    Call once at startup with all known static messages.

        precompute({
            "welcome": "Please enter a 4 digit year.",
            "cleared": "Input cleared. Please enter a 4 digit year.",
        })
    """
    for key, text in messages.items():
        print(f"Precomputing speech: {key!r}")
        _cache[key] = _synthesize(text)
    print(f"Precomputed {len(messages)} message(s).")


def play_precomputed(key: str) -> None:
    """Play a precomputed message by key. Raises KeyError if not cached."""
    samples, sample_rate = _cache[key]
    sd.play(samples, samplerate=sample_rate)


def speak(text: str) -> None:
    """Synthesize *text* on demand and play it."""
    samples, sample_rate = _synthesize(text)
    sd.play(samples, samplerate=sample_rate)


def stop() -> None:
    """Stop any currently playing speech immediately."""
    sd.stop()
