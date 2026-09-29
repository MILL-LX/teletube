"""
display.py — Draws to the framebuffer using Pillow (RGB565).

The DSI panel is portrait (480x800). We compose in landscape (800x480) and
rotate 90 degrees before writing, matching the video orientation
(mpv --video-rotate=270).

The framebuffer geometry is read from sysfs at runtime rather than assumed:
when an HDMI display is also connected the kernel makes a single large
framebuffer (e.g. 1920x1080) that both outputs share, and the DSI panel scans
out the top-left PANEL_W x PANEL_H region of it. We therefore place the panel
image in the top-left of a full-framebuffer-sized frame and honour the real
per-row byte stride, so the image is not mis-strided into a corner.
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

_FB = "/dev/fb0"
_SYS_FB = "/sys/class/graphics/fb0"

# The DSI panel's visible region (portrait). We compose landscape then rotate.
PANEL_W, PANEL_H = 480, 800          # physical portrait dimensions
LOGICAL_W, LOGICAL_H = 800, 480      # landscape compositing dimensions

_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _read_fb_geometry() -> tuple[int, int, int]:
    """Return (width, height, stride_bytes) of the framebuffer from sysfs.

    Falls back to the panel size (tightly packed RGB565) if sysfs is
    unavailable, so the module still works off-device / in tests.
    """
    try:
        w, h = (
            int(v) for v in Path(f"{_SYS_FB}/virtual_size").read_text().strip().split(",")
        )
        stride = int(Path(f"{_SYS_FB}/stride").read_text().strip())
        return w, h, stride
    except (OSError, ValueError):
        return PANEL_W, PANEL_H, PANEL_W * 2


def _rgb565_bytes(img: Image.Image) -> np.ndarray:
    """Convert an RGB image to a (H, W) uint16 array of packed RGB565 pixels."""
    arr = np.asarray(img.convert("RGB"), dtype=np.uint16)  # (H, W, 3)
    r = (arr[:, :, 0] & 0xF8) << 8
    g = (arr[:, :, 1] & 0xFC) << 3
    b = arr[:, :, 2] >> 3
    return r | g | b


class Display:
    """Renders full-screen images and text to the DSI panel region of the framebuffer."""

    def __init__(self, fb_path: str = _FB):
        self._fb_path = fb_path

    def _write(self, img: Image.Image) -> None:
        """Place the landscape *img* (rotated to portrait) into the top-left of
        the framebuffer and write the whole frame honouring its byte stride."""
        portrait = img.rotate(90, expand=True)  # -> PANEL_W x PANEL_H
        panel = _rgb565_bytes(portrait)          # (PANEL_H, PANEL_W) uint16

        fb_w, fb_h, stride = _read_fb_geometry()
        row_pixels = stride // 2                  # uint16 pixels per framebuffer row

        # Build a full-framebuffer frame (row_pixels wide to match the stride)
        # and drop the panel image into the top-left corner.
        frame = np.zeros((fb_h, row_pixels), dtype=np.uint16)
        ph, pw = panel.shape
        ph = min(ph, fb_h)
        pw = min(pw, row_pixels)
        frame[:ph, :pw] = panel[:ph, :pw]

        with open(self._fb_path, "wb") as f:
            f.write(frame.tobytes())

    def _font(self, size: int) -> ImageFont.FreeTypeFont:
        try:
            return ImageFont.truetype(_FONT_PATH, size)
        except OSError:
            return ImageFont.load_default()

    def clear(self, color: tuple[int, int, int] = (0, 0, 0)) -> None:
        """Fill the panel with a solid colour (black by default)."""
        img = Image.new("RGB", (LOGICAL_W, LOGICAL_H), color)
        self._write(img)

    def show_image(self, path: str, bg: tuple[int, int, int] = (0, 0, 0)) -> None:
        """Display the image at *path*, scaled to fit and centred on *bg*."""
        canvas = Image.new("RGB", (LOGICAL_W, LOGICAL_H), bg)
        with Image.open(path) as src:
            src = src.convert("RGB")
            src.thumbnail((LOGICAL_W, LOGICAL_H))  # fit within the panel, keep aspect
            x = (LOGICAL_W - src.width) // 2
            y = (LOGICAL_H - src.height) // 2
            canvas.paste(src, (x, y))
        self._write(canvas)

    def show_message(
        self,
        text: str,
        bg: tuple[int, int, int] = (0, 0, 0),
        fg: tuple[int, int, int] = (255, 255, 255),
        size: int = 48,
    ) -> None:
        """Draw *text* centred on a solid background.

        Newlines in *text* split it across multiple centred lines.
        """
        img = Image.new("RGB", (LOGICAL_W, LOGICAL_H), bg)
        draw = ImageDraw.Draw(img)
        font = self._font(size)

        # Anchor "mm" centres each line on the given point, so we just need to
        # place each line's centre at the right vertical position.
        lines = text.split("\n")
        ascent, descent = font.getmetrics()
        line_height = ascent + descent
        block_height = line_height * len(lines)
        start_y = (LOGICAL_H - block_height) // 2

        for i, line in enumerate(lines):
            cy = start_y + i * line_height + line_height // 2
            draw.text((LOGICAL_W // 2, cy), line, font=font, fill=fg, anchor="mm")

        self._write(img)
