#!/usr/bin/env python3
"""
debug_player.py — Testa reprodução de vídeo com mpv
Raspberry Pi 4 · mpv subprocess · PipeWire combined sink
"""

import sys
import os
import time
import signal
import subprocess

ASSETS_DIR    = os.path.join(os.path.dirname(__file__), "..", "assets")
WELCOME_VIDEO = os.path.join(ASSETS_DIR, "welcome.mp4")
DISPLAY_W     = 480
DISPLAY_H     = 320
COMBINED_SINK = "teletime_combined"
USB_SINK      = "USB Audio"

MENU = """
╔══════════════════════════════════════╗
║         DEBUG — Player (mpv)         ║
╠══════════════════════════════════════╣
║  1. Verificar mpv instalado          ║
║  2. Reproduzir welcome.mp4 (audio    ║
║     combinado: auscultador + HDMI)   ║
║  3. Reproduzir welcome.mp4 (só USB)  ║
║  4. Reproduzir welcome.mp4 (só HDMI) ║
║  5. Testar paragem por on-hook (5s)  ║
║  6. Reproduzir URL YouTube de teste  ║
║  0. Sair                             ║
╚══════════════════════════════════════╝
"""

# ── MPV helpers ───────────────────────────────────────────────────────────
def check_mpv():
    try:
        r = subprocess.run(["mpv", "--version"], capture_output=True, text=True)
        first_line = r.stdout.split("\n")[0]
        print(f"  [OK] {first_line}")
        return True
    except FileNotFoundError:
        print("  [ERRO] mpv não instalado. Corre: sudo apt install mpv")
        return False

def build_mpv_cmd(source, audio_device=None, duration=None):
    """Constrói o comando mpv com as opções corretas."""
    cmd = [
        "mpv",
        "--no-terminal",
        "--no-input-default-bindings",
        f"--geometry={DISPLAY_W}x{DISPLAY_H}+0+0",
        "--ontop",
        "--force-window=yes",
        "--vo=gpu",
    ]
    if audio_device:
        cmd += [f"--audio-device=pulse/{audio_device}"]
    if duration:
        cmd += [f"--length={duration}"]
    cmd.append(source)
    return cmd

def play_video(source, audio_device=None, duration=None, label=""):
    if not os.path.exists(source) and not source.startswith("http"):
        print(f"  [ERRO] Ficheiro não encontrado: {source}")
        print("  Coloca o ficheiro em assets/welcome.mp4")
        return None

    cmd = build_mpv_cmd(source, audio_device, duration)
    print(f"  A reproduzir{' [' + label + ']' if label else ''}...")
    print(f"  Comando: {' '.join(cmd)}")
    try:
        proc = subprocess.Popen(cmd)
        return proc
    except Exception as e:
        print(f"  [ERRO] {e}")
        return None

def wait_or_interrupt(proc, timeout=None):
    """Aguarda o fim do processo ou timeout. Devolve True se terminou normalmente."""
    start = time.time()
    try:
        while proc.poll() is None:
            elapsed = time.time() - start
            if timeout and elapsed >= timeout:
                print(f"  Timeout ({timeout}s) — a parar.")
                proc.terminate()
                proc.wait()
                return False
            time.sleep(0.1)
        rc = proc.returncode
        print(f"  Reprodução terminada (código {rc}).")
        return True
    except KeyboardInterrupt:
        proc.terminate()
        proc.wait()
        print("  Interrompido pelo utilizador.")
        return False

# ── Testes ────────────────────────────────────────────────────────────────
def test_check():
    check_mpv()
    welcome = WELCOME_VIDEO
    if os.path.exists(welcome):
        size = os.path.getsize(welcome)
        print(f"  [OK] welcome.mp4 encontrado ({size // 1024} KB)")
    else:
        print(f"  [AVISO] welcome.mp4 não encontrado: {welcome}")

def test_combined():
    proc = play_video(WELCOME_VIDEO, audio_device=COMBINED_SINK, label="combined sink")
    if proc:
        wait_or_interrupt(proc)

def test_usb():
    proc = play_video(WELCOME_VIDEO, audio_device=USB_SINK, label="USB apenas")
    if proc:
        wait_or_interrupt(proc)

def test_hdmi():
    proc = play_video(WELCOME_VIDEO, audio_device=None, label="HDMI padrão")
    if proc:
        wait_or_interrupt(proc)

def test_stop_simulation():
    print("\n  Simulação de on-hook ao fim de 5s:")
    print("  → Inicia reprodução")
    print("  → Aguarda 5s (simula threshold PLAYBACK_COMMIT_SECONDS)")
    print("  → Para o vídeo como se o telefone fosse ao gancho\n")

    proc = play_video(WELCOME_VIDEO, audio_device=COMBINED_SINK, label="teste on-hook")
    if not proc:
        return

    print("  A reproduzir... (5s)")
    time.sleep(5)

    if proc.poll() is None:
        print("  → Simulando on-hook: a parar mpv...")
        proc.terminate()
        proc.wait()
        print("  → Parado com sucesso.")
    else:
        print("  → Vídeo já terminou antes dos 5s.")

def test_youtube_url():
    url = input("  URL do vídeo YouTube para testar: ").strip()
    if not url.startswith("http"):
        print("  URL inválido.")
        return
    proc = play_video(url, audio_device=COMBINED_SINK, label="YouTube", duration=30)
    if proc:
        print("  (máximo 30s — Ctrl+C para parar antes)")
        wait_or_interrupt(proc, timeout=30)

# ── Main ──────────────────────────────────────────────────────────────────
def main():
    print(MENU)

    _proc = [None]

    def handle_exit(sig, frame):
        if _proc[0] and _proc[0].poll() is None:
            _proc[0].terminate()
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_exit)

    while True:
        try:
            choice = input("\nEscolha [0-6]: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "1":
            test_check()
        elif choice == "2":
            test_combined()
        elif choice == "3":
            test_usb()
        elif choice == "4":
            test_hdmi()
        elif choice == "5":
            test_stop_simulation()
        elif choice == "6":
            test_youtube_url()
        elif choice == "0":
            break
        else:
            print("  Opção inválida.")

if __name__ == "__main__":
    main()
