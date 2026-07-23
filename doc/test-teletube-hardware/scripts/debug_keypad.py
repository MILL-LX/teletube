#!/usr/bin/env python3
"""
debug_keypad.py — Testa o teclado 4×3 e tons DTMF
Raspberry Pi 4 · lgpio · sounddevice · numpy
"""

import sys
import time
import signal

# ── Configuração ──────────────────────────────────────────────────────────
ROW_PINS    = [16, 6, 13, 19]
COLUMN_PINS = [26, 20, 21]
OFF_HOOK_PIN = 12

KEY_MAP = [
    ["1", "2", "3"],
    ["4", "5", "6"],
    ["7", "8", "9"],
    ["*", "0", "#"],
]

DTMF_FREQS = {
    "1": (697, 1209), "2": (697, 1336), "3": (697, 1477),
    "4": (770, 1209), "5": (770, 1336), "6": (770, 1477),
    "7": (852, 1209), "8": (852, 1336), "9": (852, 1477),
    "*": (941, 1209), "0": (941, 1336), "#": (941, 1477),
}

MENU = """
╔══════════════════════════════════════╗
║         DEBUG — Keypad & DTMF        ║
╠══════════════════════════════════════╣
║  1. Scan único (todas as teclas)     ║
║  2. Monitor contínuo de teclas       ║
║  3. Tocar tom DTMF de uma tecla      ║
║  4. Tocar todos os tons DTMF         ║
║  5. Teste de varredura GPIO          ║
║  0. Sair                             ║
╚══════════════════════════════════════╝
"""

# ── GPIO ──────────────────────────────────────────────────────────────────
def init_gpio():
    try:
        import lgpio
        h = lgpio.gpiochip_open(0)
        if h < 0:
            print("[ERRO] Não foi possível abrir GPIO chip.")
            sys.exit(1)
        for row in ROW_PINS:
            lgpio.gpio_claim_output(h, row, 0)
        for col in COLUMN_PINS:
            lgpio.gpio_claim_input(h, col, lgpio.SET_PULL_DOWN)
        lgpio.gpio_claim_input(h, OFF_HOOK_PIN, lgpio.SET_PULL_UP)
        print(f"[OK] GPIO iniciado. Linhas: {ROW_PINS}  Colunas: {COLUMN_PINS}")
        return lgpio, h
    except ImportError:
        print("[ERRO] lgpio não instalado.")
        sys.exit(1)
    except Exception as e:
        print(f"[ERRO] {e}")
        sys.exit(1)

def cleanup_gpio(lgpio, h):
    try:
        for row in ROW_PINS:
            lgpio.gpio_write(h, row, 0)
        lgpio.gpiochip_close(h)
        print("[OK] GPIO libertado.")
    except Exception:
        pass

def scan_keypad(lgpio, h):
    """Devolve a tecla premida ou None."""
    for i, row in enumerate(ROW_PINS):
        for r in ROW_PINS:
            lgpio.gpio_write(h, r, 1 if r == row else 0)
        time.sleep(0.01)
        for j, col in enumerate(COLUMN_PINS):
            if lgpio.gpio_read(h, col):
                time.sleep(0.01)
                if lgpio.gpio_read(h, col):
                    key = KEY_MAP[i][j]
                    while lgpio.gpio_read(h, col):
                        time.sleep(0.05)
                    return key
    return None

# ── DTMF ──────────────────────────────────────────────────────────────────
def init_audio():
    try:
        import sounddevice as sd
        import numpy as np
        return sd, np
    except ImportError:
        print("[AVISO] sounddevice/numpy não instalados — sem audio DTMF.")
        return None, None

def play_dtmf(sd, np, digit, duration=0.5):
    if sd is None or digit not in DTMF_FREQS:
        print(f"  [AVISO] Sem audio para '{digit}'")
        return
    f1, f2 = DTMF_FREQS[digit]
    t = np.linspace(0, duration, int(44100 * duration), False)
    tone = (np.sin(2 * np.pi * f1 * t) + np.sin(2 * np.pi * f2 * t)) * 0.3
    sd.play(tone, samplerate=44100)
    sd.wait()

# ── Testes ────────────────────────────────────────────────────────────────
def test_scan_once(lgpio, h):
    print("\n  Prima uma tecla (timeout 10s)...")
    start = time.time()
    while time.time() - start < 10:
        key = scan_keypad(lgpio, h)
        if key:
            print(f"  Tecla detetada: [{key}]")
            return
        time.sleep(0.05)
    print("  Timeout — nenhuma tecla detetada.")

def test_monitor(lgpio, h, sd, np):
    print("\n  A monitorizar teclado... (Ctrl+C para parar)\n")
    buffer = ""
    try:
        while True:
            key = scan_keypad(lgpio, h)
            if key:
                ts = time.strftime("%H:%M:%S")
                print(f"  [{ts}] Tecla: [{key}]  Buffer: {buffer + key}")
                play_dtmf(sd, np, key, duration=0.3)
                buffer += key
                if len(buffer) > 8:
                    buffer = ""
            time.sleep(0.05)
    except KeyboardInterrupt:
        print(f"\n  Monitor parado. Buffer final: '{buffer}'")

def test_single_dtmf(sd, np):
    key = input("\n  Tecla para tocar DTMF [0-9 * #]: ").strip()
    if key in DTMF_FREQS:
        f1, f2 = DTMF_FREQS[key]
        print(f"  A tocar '{key}': {f1}Hz + {f2}Hz")
        play_dtmf(sd, np, key, duration=1.0)
    else:
        print(f"  Tecla '{key}' inválida.")

def test_all_dtmf(sd, np):
    print("\n  A tocar todos os tons DTMF (0.5s cada)...\n")
    for key in ["1","2","3","4","5","6","7","8","9","*","0","#"]:
        f1, f2 = DTMF_FREQS[key]
        print(f"  [{key}] — {f1}Hz + {f2}Hz")
        play_dtmf(sd, np, key, duration=0.5)
        time.sleep(0.1)
    print("  Concluído.")

def test_gpio_scan(lgpio, h):
    print("\n  Estado raw dos pinos GPIO:\n")
    for i, row in enumerate(ROW_PINS):
        for r in ROW_PINS:
            lgpio.gpio_write(h, r, 1 if r == row else 0)
        time.sleep(0.01)
        col_states = [lgpio.gpio_read(h, col) for col in COLUMN_PINS]
        print(f"  Linha GPIO{row}: colunas {COLUMN_PINS} = {col_states}")
    for r in ROW_PINS:
        lgpio.gpio_write(h, r, 0)
    hook = lgpio.gpio_read(h, OFF_HOOK_PIN)
    print(f"\n  Hook switch GPIO{OFF_HOOK_PIN}: {hook} ({'OFF-HOOK' if hook else 'ON-HOOK'})")

# ── Main ──────────────────────────────────────────────────────────────────
def main():
    print(MENU)
    lgpio, h = init_gpio()
    sd, np = init_audio()

    def handle_exit(sig, frame):
        cleanup_gpio(lgpio, h)
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_exit)

    while True:
        try:
            choice = input("\nEscolha [0-5]: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "1":
            test_scan_once(lgpio, h)
        elif choice == "2":
            test_monitor(lgpio, h, sd, np)
        elif choice == "3":
            test_single_dtmf(sd, np)
        elif choice == "4":
            test_all_dtmf(sd, np)
        elif choice == "5":
            test_gpio_scan(lgpio, h)
        elif choice == "0":
            break
        else:
            print("  Opção inválida.")

    cleanup_gpio(lgpio, h)

if __name__ == "__main__":
    main()
