from PIL import Image, ImageDraw, ImageFont
from array import array

FB = "/dev/fb0"
LOGICAL_W, LOGICAL_H = 800, 480

def to_rgb565(img):
    img = img.convert("RGB")
    pixels = array('H')  # unsigned short, 2 bytes each
    for r, g, b in img.getdata():
        pixels.append(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3))
    return pixels.tobytes()

def show_message(text, bg=(0, 0, 0), fg=(255, 255, 255), size=48):
    img = Image.new("RGB", (LOGICAL_W, LOGICAL_H), bg)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    x = (LOGICAL_W - (bbox[2] - bbox[0])) // 2
    y = (LOGICAL_H - (bbox[3] - bbox[1])) // 2
    draw.text((x, y), text, font=font, fill=fg)

    img = img.rotate(90, expand=True)

    with open(FB, "wb") as f:
        f.write(to_rgb565(img))

show_message("Hello, Pi!")