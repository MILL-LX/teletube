#!/usr/bin/env python3
"""
debug_display.py — Testa o ecrã Waveshare 480×320 via pygame
Raspberry Pi 4 · pygame
"""

import sys
import os
import signal
import time

# ── Configuração ──────────────────────────────────────────────────────────
DISPLAY_W = 480
DISPLAY_H = 320
IDLE_IMAGE = "../assets/idle_screen.png"
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

MENU = """
╔══════════════════════════════════════╗
║         DEBUG — Display              ║
╠══════════════════════════════════════╣
║  1. Ecrã preto (limpar)              ║
║  2. Mostrar imagem idle_screen.png   ║
║  3. Mostrar UI de marcação do ano    ║
║  4. Mensagem "Sem vídeos neste ano"  ║
║  5. Mensagem "A desligar..."         ║
║  6. Mensagem "A reiniciar..."        ║
║  7. Mostrar todas as telas em seq.   ║
║  0. Sair                             ║
╚══════════════════════════════════════╝
"""

# ── Pygame ────────────────────────────────────────────────────────────────
def init_display():
    try:
        import pygame
        os.environ.setdefault("DISPLAY", ":0")
        pygame.init()
        screen = pygame.display.set_mode((DISPLAY_W, DISPLAY_H))
        pygame.display.set_caption("teletime debug")
        pygame.mouse.set_visible(False)
        print(f"[OK] Display iniciado: {DISPLAY_W}×{DISPLAY_H}")
        return pygame, screen
    except ImportError:
        print("[ERRO] pygame não instalado. Corre: uv add pygame")
        sys.exit(1)
    except Exception as e:
        print(f"[ERRO] {e}")
        sys.exit(1)

def pump_events(pygame):
    """Processa eventos pygame para evitar que a janela congele."""
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return False
    return True

def show_and_wait(pygame, screen, duration=3):
    """Mostra o ecrã atual e aguarda duration segundos."""
    pygame.display.flip()
    start = time.time()
    while time.time() - start < duration:
        if not pump_events(pygame):
            return False
        time.sleep(0.05)
    return True

# ── Telas ─────────────────────────────────────────────────────────────────
def screen_black(pygame, screen):
    screen.fill((0, 0, 0))
    pygame.display.flip()
    print("  Ecrã limpo (preto).")

def screen_idle(pygame, screen):
    img_path = os.path.join(ASSETS_DIR, "idle_screen.png")
    screen.fill((0, 0, 0))
    if os.path.exists(img_path):
        try:
            img = pygame.image.load(img_path)
            img = pygame.transform.scale(img, (DISPLAY_W, DISPLAY_H))
            screen.blit(img, (0, 0))
            print(f"  Imagem carregada: {img_path}")
        except Exception as e:
            print(f"  [AVISO] Não foi possível carregar imagem: {e}")
            _draw_placeholder(pygame, screen, "idle_screen.png", (40, 40, 40))
    else:
        print(f"  [AVISO] Ficheiro não encontrado: {img_path}")
        _draw_placeholder(pygame, screen, "idle_screen.png em falta", (40, 40, 40))
    show_and_wait(pygame, screen, 4)

def screen_year_input(pygame, screen, digits=""):
    screen.fill((10, 10, 20))
    font_big  = pygame.font.SysFont("monospace", 72, bold=True)
    font_med  = pygame.font.SysFont("monospace", 28)
    font_small = pygame.font.SysFont("monospace", 20)

    # Título
    title = font_med.render("Marca o ano", True, (180, 180, 180))
    screen.blit(title, (DISPLAY_W // 2 - title.get_width() // 2, 40))

    # Dígitos com slots
    slots = []
    for i in range(4):
        ch = digits[i] if i < len(digits) else "_"
        color = (255, 220, 50) if i < len(digits) else (80, 80, 100)
        slots.append(font_big.render(ch, True, color))

    total_w = sum(s.get_width() for s in slots) + 3 * 30
    x = (DISPLAY_W - total_w) // 2
    y = 110
    for s in slots:
        screen.blit(s, (x, y))
        x += s.get_width() + 30

    # Instrução
    hint = font_small.render("Prima # para confirmar", True, (100, 100, 120))
    screen.blit(hint, (DISPLAY_W // 2 - hint.get_width() // 2, 240))

    show_and_wait(pygame, screen, 3)

def screen_no_videos(pygame, screen):
    screen.fill((20, 10, 10))
    font_big  = pygame.font.SysFont("monospace", 36, bold=True)
    font_med  = pygame.font.SysFont("monospace", 22)

    msg1 = font_big.render("Sem vídeos", True, (220, 80, 60))
    msg2 = font_med.render("neste ano", True, (180, 100, 80))
    hint = font_med.render("Tenta outro ano", True, (120, 120, 120))

    screen.blit(msg1, (DISPLAY_W // 2 - msg1.get_width() // 2, 90))
    screen.blit(msg2, (DISPLAY_W // 2 - msg2.get_width() // 2, 145))
    screen.blit(hint, (DISPLAY_W // 2 - hint.get_width() // 2, 210))

    show_and_wait(pygame, screen, 3)

def screen_shutdown(pygame, screen):
    _screen_system_msg(pygame, screen, "A desligar...", (220, 80, 60))

def screen_reboot(pygame, screen):
    _screen_system_msg(pygame, screen, "A reiniciar...", (60, 180, 120))

def _screen_system_msg(pygame, screen, msg, color):
    screen.fill((5, 5, 5))
    font = pygame.font.SysFont("monospace", 42, bold=True)
    text = font.render(msg, True, color)
    screen.blit(text, (DISPLAY_W // 2 - text.get_width() // 2,
                       DISPLAY_H // 2 - text.get_height() // 2))
    show_and_wait(pygame, screen, 3)

def _draw_placeholder(pygame, screen, label, color):
    pygame.draw.rect(screen, color, (20, 20, DISPLAY_W - 40, DISPLAY_H - 40), 2)
    font = pygame.font.SysFont("monospace", 18)
    text = font.render(f"[ {label} ]", True, (150, 150, 150))
    screen.blit(text, (DISPLAY_W // 2 - text.get_width() // 2,
                       DISPLAY_H // 2 - text.get_height() // 2))

def test_sequence(pygame, screen):
    print("\n  A mostrar todas as telas em sequência (3s cada)...\n")
    screens = [
        ("Preto",              lambda: screen_black(pygame, screen)),
        ("Idle image",         lambda: screen_idle(pygame, screen)),
        ("Marcação '19'",      lambda: screen_year_input(pygame, screen, "19")),
        ("Marcação '1985'",    lambda: screen_year_input(pygame, screen, "1985")),
        ("Sem vídeos",         lambda: screen_no_videos(pygame, screen)),
        ("A desligar",         lambda: screen_shutdown(pygame, screen)),
        ("A reiniciar",        lambda: screen_reboot(pygame, screen)),
    ]
    for name, fn in screens:
        print(f"  → {name}")
        fn()
    print("  Sequência concluída.")

# ── Main ──────────────────────────────────────────────────────────────────
def main():
    print(MENU)
    pygame, screen = init_display()

    def handle_exit(sig, frame):
        pygame.quit()
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_exit)

    screen_black(pygame, screen)

    while True:
        try:
            choice = input("\nEscolha [0-7]: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "1":
            screen_black(pygame, screen)
        elif choice == "2":
            screen_idle(pygame, screen)
        elif choice == "3":
            digits = input("  Dígitos a mostrar (0-4 chars, ex: '19'): ").strip()[:4]
            screen_year_input(pygame, screen, digits)
        elif choice == "4":
            screen_no_videos(pygame, screen)
        elif choice == "5":
            screen_shutdown(pygame, screen)
        elif choice == "6":
            screen_reboot(pygame, screen)
        elif choice == "7":
            test_sequence(pygame, screen)
        elif choice == "0":
            break
        else:
            print("  Opção inválida.")

    screen_black(pygame, screen)
    pygame.quit()

if __name__ == "__main__":
    main()
