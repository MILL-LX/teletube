"""
sound/speech.py — Text-to-speech via Piper TTS.

The voice model is loaded when this module is imported. Audio is played
through sounddevice (same stack as DtmfPlayer) rather than aplay.

Synthesized audio is persisted to sound/speech_cache/<key>.npz. On
subsequent runs the synthesis step is skipped for any key already on disk.

Call precompute() with a dict of {key: text} to load or synthesize messages
at startup, then use play_precomputed(key) to play them instantly.

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
_CACHE_DIR  = Path(__file__).parent / "speech_cache"

print(f"Loading voice model: {_MODEL_PATH}")
_voice = PiperVoice.load(str(_MODEL_PATH))
print("Voice model loaded.")

_CACHE_DIR.mkdir(exist_ok=True)

# In-memory cache: key -> (samples: np.ndarray, sample_rate: int)
_cache: dict[str, tuple[np.ndarray, int]] = {}


def _synthesize(text: str) -> tuple[np.ndarray, int]:
    """Synthesize *text* via Piper and return (float32 samples, sample_rate)."""
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
    """Load or synthesize each text in *messages* and cache it under its key.

    The key is used as the filename in speech_cache/, so previously
    synthesized messages are loaded from disk without re-running Piper.

        precompute({
            "welcome": "Please enter a 4 digit year.",
            "cleared": "Input cleared. Please enter a 4 digit year.",
        })
    """
    for key, text in messages.items():
        path = _CACHE_DIR / f"{key}.npz"
        if path.exists():
            data = np.load(path)
            _cache[key] = data["samples"], int(data["sample_rate"])
        else:
            print(f"Synthesizing: {key!r}")
            samples, sample_rate = _synthesize(text)
            np.savez(path, samples=samples, sample_rate=np.array(sample_rate))
            _cache[key] = samples, sample_rate
    print(f"Speech cache ready: {len(messages)} message(s).")


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
