#!/usr/bin/env python3
"""
debug_audio.py — Testa dispositivos de audio e combined sink PipeWire
Raspberry Pi 4 · sounddevice · subprocess
"""

import sys
import time
import signal
import subprocess

MENU = """
╔══════════════════════════════════════╗
║         DEBUG — Audio                ║
╠══════════════════════════════════════╣
║  1. Listar dispositivos (aplay)      ║
║  2. Listar dispositivos (sounddevice)║
║  3. Listar sinks PipeWire/Pulse      ║
║  4. Tocar tom no USB Audio Device    ║
║  5. Tocar tom no HDMI                ║
║  6. Tocar tom no combined sink       ║
║  7. Tocar tom em TODOS os sinks      ║
║  0. Sair                             ║
╚══════════════════════════════════════╝
"""

USB_HINT      = "USB Audio"
HDMI_HINT     = "bcm2835 Headphones"
COMBINED_HINT = "teletime_combined"

# ── Audio ─────────────────────────────────────────────────────────────────
def init_audio():
    try:
        import sounddevice as sd
        import numpy as np
        return sd, np
    except ImportError:
        print("[ERRO] sounddevice/numpy não instalados.")
        sys.exit(1)

def gen_tone(np, freq=440, duration=1.5, sr=44100):
    t = np.linspace(0, duration, int(sr * duration), False)
    return (np.sin(2 * np.pi * freq * t) * 0.4).astype("float32")

def find_device(sd, hint):
    for i, d in enumerate(sd.query_devices()):
        if hint.lower() in d["name"].lower() and d["max_output_channels"] > 0:
            return i, d["name"]
    return None, None

def play_on_device(sd, np, device_id, device_name, freq=440):
    tone = gen_tone(np, freq=freq)
    print(f"  A tocar {freq}Hz em: [{device_name}] (1.5s)...")
    try:
        sd.play(tone, samplerate=44100, device=device_id)
        sd.wait()
        print("  OK.")
    except Exception as e:
        print(f"  [ERRO] {e}")

# ── Testes ────────────────────────────────────────────────────────────────
def test_aplay():
    print("\n  --- aplay -l ---")
    try:
        result = subprocess.run(["aplay", "-l"], capture_output=True, text=True)
        print(result.stdout or "  (sem output)")
        if result.stderr:
            print(f"  [AVISO] {result.stderr.strip()}")
    except FileNotFoundError:
        print("  [ERRO] aplay não encontrado.")

def test_sounddevice_list(sd):
    print("\n  --- Dispositivos sounddevice (output) ---\n")
    for i, d in enumerate(sd.query_devices()):
        if d["max_output_channels"] > 0:
            print(f"  [{i:2d}] {d['name']}")
            print(f"        canais: {d['max_output_channels']}  sr: {int(d['default_samplerate'])}Hz")

def test_pipewire_sinks():
    print("\n  --- pactl list short sinks ---")
    try:
        result = subprocess.run(["pactl", "list", "short", "sinks"],
                                capture_output=True, text=True)
        lines = result.stdout.strip().split("\n")
        if not lines or lines == [""]:
            print("  (nenhum sink encontrado)")
        else:
            for line in lines:
                marker = " <-- combined" if COMBINED_HINT in line else ""
                print(f"  {line}{marker}")
        if COMBINED_HINT not in result.stdout:
            print(f"\n  [AVISO] '{COMBINED_HINT}' não encontrado.")
            print("  Verifica a secção 5 do manual (PipeWire combined sink).")
    except FileNotFoundError:
        print("  [ERRO] pactl não encontrado — PipeWire não instalado?")

def test_usb(sd, np):
    dev_id, dev_name = find_device(sd, USB_HINT)
    if dev_id is None:
        print(f"  [ERRO] Dispositivo '{USB_HINT}' não encontrado.")
        print("  Verifica se o adaptador USB Audio está ligado.")
        return
    play_on_device(sd, np, dev_id, dev_name, freq=440)

def test_hdmi(sd, np):
    dev_id, dev_name = find_device(sd, HDMI_HINT)
    if dev_id is None:
        print(f"  [ERRO] Dispositivo '{HDMI_HINT}' não encontrado.")
        print("  Verifica se o HDMI está ligado e configurado.")
        return
    play_on_device(sd, np, dev_id, dev_name, freq=550)

def test_combined(sd, np):
    dev_id, dev_name = find_device(sd, COMBINED_HINT)
    if dev_id is None:
        print(f"  [ERRO] Combined sink '{COMBINED_HINT}' não encontrado.")
        print("  Segue a secção 5 do manual para criar o combined sink.")
        return
    play_on_device(sd, np, dev_id, dev_name, freq=660)

def test_all(sd, np):
    print("\n  A tocar em todos os sinks conhecidos...\n")
    targets = [
        (USB_HINT,      440, "USB Audio (auscultador)"),
        (HDMI_HINT,     550, "HDMI"),
        (COMBINED_HINT, 660, "Combined sink (duplo)"),
    ]
    for hint, freq, label in targets:
        dev_id, dev_name = find_device(sd, hint)
        if dev_id is not None:
            print(f"  [{label}]")
            play_on_device(sd, np, dev_id, dev_name, freq=freq)
        else:
            print(f"  [{label}] — não encontrado, a saltar.")
        time.sleep(0.3)

# ── Main ──────────────────────────────────────────────────────────────────
def main():
    print(MENU)
    sd, np = init_audio()

    def handle_exit(sig, frame):
        try:
            sd.stop()
        except Exception:
            pass
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_exit)

    while True:
        try:
            choice = input("\nEscolha [0-7]: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "1":
            test_aplay()
        elif choice == "2":
            test_sounddevice_list(sd)
        elif choice == "3":
            test_pipewire_sinks()
        elif choice == "4":
            test_usb(sd, np)
        elif choice == "5":
            test_hdmi(sd, np)
        elif choice == "6":
            test_combined(sd, np)
        elif choice == "7":
            test_all(sd, np)
        elif choice == "0":
            break
        else:
            print("  Opção inválida.")

if __name__ == "__main__":
    main()
