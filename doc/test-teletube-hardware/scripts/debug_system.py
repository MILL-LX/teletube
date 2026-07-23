#!/usr/bin/env python3
"""
debug_system.py — Testa códigos de sistema (shutdown/reboot)
Modo simulado por defeito — nunca executa sem confirmação explícita
Raspberry Pi 4
"""

import sys
import os
import time
import signal
import subprocess

MENU = """
╔══════════════════════════════════════╗
║         DEBUG — Sistema              ║
╠══════════════════════════════════════╣
║  1. Verificar permissões sudoers     ║
║  2. Simular shutdown (sem executar)  ║
║  3. Simular reboot  (sem executar)   ║
║  4. Testar deteção de código 0000    ║
║  5. Testar deteção de código 1111    ║
║  -- PERIGO: execução real --         ║
║  6. EXECUTAR shutdown (real)         ║
║  7. EXECUTAR reboot  (real)          ║
║  0. Sair                             ║
╚══════════════════════════════════════╝
"""

# ── Sudoers ───────────────────────────────────────────────────────────────
def test_sudoers():
    print("\n  A verificar permissões sudo para shutdown/reboot...\n")

    checks = [
        (["sudo", "-n", "shutdown", "--help"],  "shutdown"),
        (["sudo", "-n", "reboot",   "--help"],  "reboot"),
    ]

    all_ok = True
    for cmd, label in checks:
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=5)
            if r.returncode == 0:
                print(f"  [OK] sudo {label} — sem password")
            else:
                print(f"  [FALHOU] sudo {label} — requer password ou não configurado")
                print(f"  Segue a secção 10.1 do manual para configurar /etc/sudoers.d/teletime")
                all_ok = False
        except subprocess.TimeoutExpired:
            print(f"  [FALHOU] sudo {label} — timeout")
            all_ok = False
        except Exception as e:
            print(f"  [ERRO] {e}")
            all_ok = False

    if all_ok:
        print("\n  Permissões OK — o teletime pode executar shutdown/reboot sem password.")
    else:
        print("\n  Cria o ficheiro com:")
        print("    sudo visudo -f /etc/sudoers.d/teletime")
        print(f"  Conteúdo (substitui 'pi' pelo teu user):")
        print("    pi ALL=(ALL) NOPASSWD: /sbin/shutdown, /sbin/reboot")

# ── Simulação ─────────────────────────────────────────────────────────────
def simulate_shutdown():
    print("\n  [SIMULAÇÃO] Código 0000# detetado")
    print("  → Para todos os processos (mpv, audio, pygame)")
    print("  → display.py mostra: 'A desligar...'")
    print("  → Aguarda 2 segundos")
    print("  → Executaria: subprocess.run(['sudo', 'shutdown', '-h', 'now'])")
    print("\n  (Nada foi executado — modo simulação)")
    _show_system_screen("A desligar...", "(0000#)")

def simulate_reboot():
    print("\n  [SIMULAÇÃO] Código 1111# detetado")
    print("  → Para todos os processos (mpv, audio, pygame)")
    print("  → display.py mostra: 'A reiniciar...'")
    print("  → Aguarda 2 segundos")
    print("  → Executaria: subprocess.run(['sudo', 'reboot'])")
    print("\n  (Nada foi executado — modo simulação)")
    _show_system_screen("A reiniciar...", "(1111#)")

def _show_system_screen(msg, subtitle):
    """Tenta mostrar a mensagem no ecrã se pygame disponível."""
    try:
        import pygame
        os.environ.setdefault("DISPLAY", ":0")
        pygame.init()
        screen = pygame.display.set_mode((480, 320))
        pygame.mouse.set_visible(False)
        screen.fill((5, 5, 5))
        font_big = pygame.font.SysFont("monospace", 42, bold=True)
        font_sm  = pygame.font.SysFont("monospace", 20)
        color    = (220, 80, 60) if "desligar" in msg else (60, 180, 120)
        text = font_big.render(msg, True, color)
        sub  = font_sm.render(subtitle, True, (80, 80, 80))
        screen.blit(text, (240 - text.get_width() // 2, 130))
        screen.blit(sub,  (240 - sub.get_width()  // 2, 200))
        pygame.display.flip()
        print("  Mensagem exibida no ecrã por 3s...")
        time.sleep(3)
        pygame.quit()
    except ImportError:
        print("  (pygame não disponível — sem preview no ecrã)")
    except Exception as e:
        print(f"  (ecrã não disponível: {e})")

# ── Deteção de código ─────────────────────────────────────────────────────
def test_code_detection(code):
    """Simula a lógica de deteção de código no main.py."""
    SYSTEM_CODES = {
        "0000": ("shutdown", "A desligar..."),
        "1111": ("reboot",   "A reiniciar..."),
    }

    print(f"\n  Simulando marcação do código '{code}#'...\n")

    # Simula digitação tecla a tecla
    buffer = ""
    for digit in code:
        buffer += digit
        print(f"  Tecla '{digit}' → buffer: '{buffer}'")
        time.sleep(0.3)

    print(f"  Tecla '#' → confirma código '{buffer}'")

    if buffer in SYSTEM_CODES:
        action, msg = SYSTEM_CODES[buffer]
        print(f"\n  [MATCH] Código '{buffer}' reconhecido → ação: {action}")
        print(f"  Mensagem no ecrã: '{msg}'")
        print("  (em produção, executaria o comando de sistema)")
    else:
        print(f"\n  Código '{buffer}' não reconhecido como código de sistema.")
        print(f"  Seria tratado como ano: validação {int(buffer)} entre 2007-{YEAR_MAX}?")
        year = int(buffer)
        if 2007 <= year <= YEAR_MAX:
            print(f"  Sim — buscaria vídeos de {year}.")
        else:
            print(f"  Não — ano inválido, mostraria erro.")

# ── Execução real ─────────────────────────────────────────────────────────
def execute_shutdown():
    print("\n  !! ATENÇÃO: Vai executar sudo shutdown -h now !!")
    resp = input("  Tens a certeza? Escreve 'DESLIGAR' para confirmar: ").strip()
    if resp == "DESLIGAR":
        print("  A desligar em 3 segundos...")
        time.sleep(3)
        subprocess.run(["sudo", "shutdown", "-h", "now"])
    else:
        print("  Cancelado.")

def execute_reboot():
    print("\n  !! ATENÇÃO: Vai executar sudo reboot !!")
    resp = input("  Tens a certeza? Escreve 'REINICIAR' para confirmar: ").strip()
    if resp == "REINICIAR":
        print("  A reiniciar em 3 segundos...")
        time.sleep(3)
        subprocess.run(["sudo", "reboot"])
    else:
        print("  Cancelado.")

# ── Main ──────────────────────────────────────────────────────────────────
def main():
    print(MENU)

    def handle_exit(sig, frame):
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_exit)

    while True:
        try:
            choice = input("\nEscolha [0-7]: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "1":
            test_sudoers()
        elif choice == "2":
            simulate_shutdown()
        elif choice == "3":
            simulate_reboot()
        elif choice == "4":
            test_code_detection("0000")
        elif choice == "5":
            test_code_detection("1111")
        elif choice == "6":
            execute_shutdown()
        elif choice == "7":
            execute_reboot()
        elif choice == "0":
            break
        else:
            print("  Opção inválida.")

if __name__ == "__main__":
    main()
