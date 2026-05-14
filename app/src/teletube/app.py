import pygame
import pygame._freetype
pygame.init()
pygame._freetype.init()

screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
W, H = screen.get_size()

font = pygame._freetype.Font(None, 72)

def show_message(text, bg=(0,0,0), fg=(255,255,255)):
    screen.fill(bg)
    text_surf, rect = font.render(text, fg)
    text_surf = pygame.transform.rotate(text_surf, 90) 
    rect = text_surf.get_rect(center=(W // 2, H // 2))
    screen.blit(text_surf, rect)
    pygame.display.flip()

show_message("Hello, Pi!")

while True:
    for e in pygame.event.get():
        if e.type in (pygame.QUIT, pygame.KEYDOWN):
            pygame.quit()
            raise SystemExit
        