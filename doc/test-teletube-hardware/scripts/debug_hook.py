#!/usr/bin/env python3
"""
debug_hook.py — Testa o hook switch do telefone (GPIO 12)
Raspberry Pi 4 · lgpio
"""

import sys
import time
import signal

# ── Configuração ──────────────────────────────────────────────────────────
OFF_HOOK_PIN = 12
POLL_INTERVAL = 0.05  # segundos entre leituras

# ── Menu ──────────────────────────────────────────────────────────────────
MENU = """
╔══════════════════════════════════════╗
║         DEBUG — Hook Switch          ║
╠══════════════════════════════════════╣
║  1. Leitura única do estado atual    ║
║  2. Monitor contínuo (Ctrl+C para    ║
║     parar)                           ║
║  3. Contar eventos on/off-hook       ║
║  0. Sair                             ║
╚══════════════════════════════════════╝
"""

def init_gpio():
    try:
        import lgpio
        h = lgpio.gpiochip_open(0)
        if h < 0:
            print("[ERRO] Não foi possível abrir o GPIO chip.")
            sys.exit(1)
        lgpio.gpio_claim_input(h, OFF_HOOK_PIN, lgpio.SET_PULL_UP)
        print(f"[OK] GPIO {OFF_HOOK_PIN} iniciado com pull-up.")
        return lgpio, h
    except ImportError:
        print("[ERRO] lgpio não está instalado. Corre: uv add lgpio")
        sys.exit(1)
    except Exception as e:
        print(f"[ERRO] Falha ao iniciar GPIO: {e}")
        sys.exit(1)

def cleanup(lgpio, h):
    try:
        lgpio.gpiochip_close(h)
        print("\n[OK] GPIO libertado.")
    except Exception:
        pass

def read_state(lgpio, h):
    val = lgpio.gpio_read(h, OFF_HOOK_PIN)
    return val == 1

def test_single(lgpio, h):
    state = read_state(lgpio, h)
    label = "OFF-HOOK (auscultador levantado)" if state else "ON-HOOK  (auscultador pousado)"
    print(f"\n  Estado atual: {label}")
    print(f"  Valor GPIO {OFF_HOOK_PIN}: {1 if state else 0}")

def test_monitor(lgpio, h):
    print("\n  A monitorizar hook switch... (Ctrl+C para parar)\n")
    last_state = None
    try:
        while True:
            state = read_state(lgpio, h)
            if state != last_state:
                label = "OFF-HOOK >> auscultador LEVANTADO" if state else "ON-HOOK  >> auscultador POUSADO"
                ts = time.strftime("%H:%M:%S")
                print(f"  [{ts}] {label}")
                last_state = state
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\n  Monitor parado.")

def test_count(lgpio, h):
    print("\n  A contar eventos... (Ctrl+C para parar)\n")
    count_off = 0
    count_on = 0
    last_state = read_state(lgpio, h)
    try:
        while True:
            state = read_state(lgpio, h)
            if state != last_state:
                if state:
                    count_off += 1
                    print(f"  OFF-HOOK #{count_off}")
                else:
                    count_on += 1
                    print(f"  ON-HOOK  #{count_on}")
                last_state = state
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print(f"\n  Total: {count_off} off-hook, {count_on} on-hook")

def main():
    print(MENU)
    lgpio, h = init_gpio()

    def handle_exit(sig, frame):
        cleanup(lgpio, h)
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_exit)

    while True:
        try:
            choice = input("\nEscolha [0-3]: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "1":
            test_single(lgpio, h)
        elif choice == "2":
            test_monitor(lgpio, h)
        elif choice == "3":
            test_count(lgpio, h)
        elif choice == "0":
            break
        else:
            print("  Opção inválida.")

    cleanup(lgpio, h)

if __name__ == "__main__":
    main()
