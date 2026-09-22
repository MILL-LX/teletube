"""
display.py — Draws to the framebuffer using Pillow (RGB565).

The physical framebuffer is portrait (480x800). We draw in landscape
(800x480) and rotate 90 degrees before writing, matching the orientation
used for video playback (mpv --video-rotate=270).
"""

from array import array
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_FB = "/dev/fb0"
LOGICAL_W, LOGICAL_H = 800, 480

_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _to_rgb565(img: Image.Image) -> bytes:
    """Convert an RGB image to packed RGB565 bytes for the framebuffer."""
    img = img.convert("RGB")
    pixels = array("H")  # unsigned short, 2 bytes each
    for r, g, b in img.getdata():
        pixels.append(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3))
    return pixels.tobytes()


class Display:
    """Renders full-screen images and text to the framebuffer."""

    def __init__(self, fb_path: str = _FB):
        self._fb_path = fb_path

    def _write(self, img: Image.Image) -> None:
        """Rotate a landscape image to the physical orientation and write it."""
        img = img.rotate(90, expand=True)
        with open(self._fb_path, "wb") as f:
            f.write(_to_rgb565(img))

    def _font(self, size: int) -> ImageFont.FreeTypeFont:
        try:
            return ImageFont.truetype(_FONT_PATH, size)
        except OSError:
            return ImageFont.load_default()

    def clear(self, color: tuple[int, int, int] = (0, 0, 0)) -> None:
        """Fill the screen with a solid colour (black by default)."""
        img = Image.new("RGB", (LOGICAL_W, LOGICAL_H), color)
        self._write(img)

    def show_message(
        self,
        text: str,
        bg: tuple[int, int, int] = (0, 0, 0),
        fg: tuple[int, int, int] = (255, 255, 255),
        size: int = 48,
    ) -> None:
        """Draw *text* centred on a solid background."""
        img = Image.new("RGB", (LOGICAL_W, LOGICAL_H), bg)
        draw = ImageDraw.Draw(img)
        font = self._font(size)

        bbox = draw.textbbox((0, 0), text, font=font)
        x = (LOGICAL_W - (bbox[2] - bbox[0])) // 2
        y = (LOGICAL_H - (bbox[3] - bbox[1])) // 2
        draw.text((x, y), text, font=font, fill=fg)

        self._write(img)
