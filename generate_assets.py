"""Génère les illustrations de secours des pièces.

Le salon utilise l'image fournie par l'auteur du jeu. Les autres images sont des
silhouettes gothiques procédurales conçues pour rester lisibles après conversion
ASCII. Elles peuvent être remplacées librement par des PNG/JPG portant les mêmes
noms dans ``assets/rooms``.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "assets" / "rooms"
WIDTH, HEIGHT = 960, 540


def gradient_background(seed: int, horizon: int = 360) -> Image.Image:
    random.seed(seed)
    image = Image.new("RGB", (WIDTH, HEIGHT), (15, 12, 13))
    pixels = image.load()
    for y in range(HEIGHT):
        vertical = y / HEIGHT
        for x in range(WIDTH):
            radial = math.hypot((x - WIDTH * 0.5) / WIDTH, (y - horizon) / HEIGHT)
            noise = random.randint(-5, 5)
            warm = max(0, 1 - radial * 1.3)
            r = int(17 + 37 * warm + 10 * vertical + noise)
            g = int(14 + 25 * warm + 6 * vertical + noise * 0.5)
            b = int(16 + 20 * warm + 3 * vertical + noise * 0.4)
            pixels[x, y] = (max(0, r), max(0, g), max(0, b))
    return image.filter(ImageFilter.GaussianBlur(0.6))


def vignette(image: Image.Image) -> Image.Image:
    mask = Image.new("L", image.size, 0)
    px = mask.load()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            nx = (x - WIDTH / 2) / (WIDTH / 2)
            ny = (y - HEIGHT / 2) / (HEIGHT / 2)
            dist = min(1.0, math.sqrt(nx * nx + ny * ny))
            px[x, y] = int(255 * max(0.0, 1.0 - dist**1.8))
    dark = Image.new("RGB", image.size, (0, 0, 0))
    return Image.composite(image, dark, ImageOps.invert(mask).point(lambda p: int(p * 0.52)))


def add_floor(draw: ImageDraw.ImageDraw, horizon: int = 360) -> None:
    draw.polygon([(0, horizon), (WIDTH, horizon), (WIDTH, HEIGHT), (0, HEIGHT)], fill=(32, 24, 22))
    for x in range(0, WIDTH, 55):
        draw.line((WIDTH // 2, horizon, x, HEIGHT), fill=(58, 43, 37), width=2)
    for y in range(horizon + 20, HEIGHT, 28):
        draw.line((0, y, WIDTH, y), fill=(49, 36, 32), width=2)


def add_wall_panels(draw: ImageDraw.ImageDraw, horizon: int = 360) -> None:
    draw.rectangle((0, 0, WIDTH, horizon), outline=(92, 67, 48), width=8)
    for x in range(40, WIDTH - 70, 180):
        outer_right = min(x + 140, WIDTH - 20)
        inner_right = min(x + 125, WIDTH - 35)
        if outer_right > x:
            draw.rectangle((x, 60, outer_right, horizon - 25), outline=(77, 55, 43), width=5)
        if inner_right > x + 15:
            draw.rectangle((x + 15, 80, inner_right, horizon - 45), outline=(48, 35, 32), width=3)


def add_dust(image: Image.Image, seed: int) -> None:
    random.seed(seed)
    draw = ImageDraw.Draw(image, "RGBA")
    for _ in range(520):
        x = random.randrange(WIDTH)
        y = random.randrange(HEIGHT)
        radius = random.choice((1, 1, 1, 2))
        alpha = random.randrange(8, 35)
        draw.ellipse((x, y, x + radius, y + radius), fill=(225, 210, 175, alpha))


def save_scene(name: str, image: Image.Image, seed: int) -> None:
    add_dust(image, seed)
    image = ImageEnhance.Contrast(image).enhance(1.13)
    image = vignette(image)
    image.save(ASSET_DIR / f"{name}.png", optimize=True)


def scene_cuisine() -> Image.Image:
    im = gradient_background(2)
    d = ImageDraw.Draw(im)
    add_floor(d)
    add_wall_panels(d)
    d.rectangle((620, 120, 845, 355), fill=(42, 42, 40), outline=(120, 108, 90), width=7)
    d.rectangle((650, 150, 815, 245), outline=(86, 84, 75), width=5)
    d.ellipse((790, 278, 806, 294), fill=(160, 145, 112))
    d.polygon([(250, 300), (590, 300), (680, 430), (160, 430)], fill=(48, 32, 25), outline=(126, 86, 58))
    for x in (220, 580):
        d.line((x, 420, x - 30, 520), fill=(68, 46, 34), width=12)
    for x in (350, 455, 560):
        d.ellipse((x, 55, x + 80, 135), outline=(124, 90, 62), width=8)
        d.line((x + 40, 0, x + 40, 55), fill=(110, 82, 57), width=5)
    return im


def scene_couloir() -> Image.Image:
    im = gradient_background(3, horizon=390)
    d = ImageDraw.Draw(im)
    d.polygon([(0, 0), (260, 115), (260, 390), (0, HEIGHT)], fill=(37, 28, 27), outline=(98, 71, 56))
    d.polygon([(WIDTH, 0), (700, 115), (700, 390), (WIDTH, HEIGHT)], fill=(35, 27, 28), outline=(98, 71, 56))
    d.rectangle((260, 115, 700, 390), fill=(42, 31, 31), outline=(100, 73, 58), width=7)
    d.rectangle((410, 145, 555, 295), fill=(24, 24, 25), outline=(148, 105, 70), width=12)
    d.ellipse((445, 175, 520, 250), fill=(58, 58, 54), outline=(115, 92, 70), width=5)
    d.polygon([(260, 390), (700, 390), (WIDTH, HEIGHT), (0, HEIGHT)], fill=(29, 22, 22))
    for x in range(0, WIDTH, 90):
        d.line((480, 390, x, HEIGHT), fill=(62, 45, 39), width=2)
    return im


def scene_bibliotheque() -> Image.Image:
    im = gradient_background(4)
    d = ImageDraw.Draw(im)
    add_floor(d)
    for start in (40, 340, 640):
        d.rectangle((start, 35, start + 260, 360), fill=(35, 24, 23), outline=(105, 70, 47), width=10)
        for y in range(75, 345, 52):
            d.line((start + 10, y, start + 250, y), fill=(112, 77, 51), width=7)
            x = start + 20
            while x < start + 240:
                w = random.randint(8, 20)
                h = random.randint(31, 47)
                d.rectangle((x, y - h, x + w, y - 3), fill=random.choice([(69, 38, 31), (47, 48, 39), (68, 54, 31), (45, 37, 49)]))
                x += w + random.randint(3, 7)
    d.rectangle((360, 290, 600, 440), fill=(31, 27, 25), outline=(143, 112, 77), width=8)
    d.rectangle((388, 315, 572, 410), outline=(98, 135, 130), width=5)
    d.line((760, 80, 600, 440), fill=(123, 88, 57), width=12)
    for y in range(140, 410, 55):
        d.line((710 - (y - 140) * 0.28, y, 755 - (y - 140) * 0.28, y), fill=(116, 81, 53), width=7)
    return im


def scene_salle_a_manger() -> Image.Image:
    im = gradient_background(5)
    d = ImageDraw.Draw(im)
    add_floor(d)
    add_wall_panels(d)
    d.polygon([(190, 300), (770, 300), (875, 430), (85, 430)], fill=(42, 27, 23), outline=(132, 88, 58), width=7)
    for x in (150, 800):
        d.line((x, 420, x - 15 if x < 400 else x + 15, 525), fill=(71, 48, 35), width=15)
    d.line((480, 0, 480, 105), fill=(108, 77, 55), width=6)
    d.ellipse((390, 90, 570, 180), outline=(152, 113, 78), width=8)
    for x in (410, 450, 490, 530):
        d.line((x, 145, x - 25, 225), fill=(115, 84, 61), width=4)
        d.ellipse((x - 37, 213, x - 15, 235), fill=(185, 151, 101))
    d.rectangle((770, 85, 910, 300), fill=(25, 25, 24), outline=(111, 79, 55), width=8)
    return im


def scene_vestibule() -> Image.Image:
    im = gradient_background(6)
    d = ImageDraw.Draw(im)
    add_floor(d)
    add_wall_panels(d)
    d.rectangle((340, 65, 620, 360), fill=(30, 24, 24), outline=(123, 87, 58), width=13)
    d.line((480, 78, 480, 350), fill=(106, 72, 49), width=8)
    for x in (390, 530):
        d.rectangle((x, 120, x + 75, 280), outline=(80, 58, 46), width=5)
        d.ellipse((x + 50, 210, x + 62, 222), fill=(180, 144, 88))
    d.line((175, 125, 175, 390), fill=(88, 60, 47), width=10)
    for dx in (-55, 0, 55):
        d.line((175, 145, 175 + dx, 95), fill=(88, 60, 47), width=7)
    d.ellipse((130, 380, 220, 420), outline=(104, 74, 55), width=7)
    return im


def scene_palier() -> Image.Image:
    im = gradient_background(7)
    d = ImageDraw.Draw(im)
    add_floor(d)
    add_wall_panels(d)
    d.polygon([(420, 360), (540, 360), (650, 540), (310, 540)], fill=(28, 21, 22))
    d.line((420, 360, 310, 540), fill=(115, 77, 52), width=8)
    d.line((540, 360, 650, 540), fill=(115, 77, 52), width=8)
    for x in (90, 720):
        d.rectangle((x, 105, x + 150, 300), fill=(28, 27, 27), outline=(137, 98, 65), width=10)
        d.ellipse((x + 45, 145, x + 105, 230), fill=(69, 60, 55))
    return im


def scene_chambre_maitre() -> Image.Image:
    im = gradient_background(8)
    d = ImageDraw.Draw(im)
    add_floor(d)
    add_wall_panels(d)
    d.rectangle((180, 225, 650, 410), fill=(47, 35, 34), outline=(120, 83, 61), width=9)
    d.polygon([(210, 180), (600, 180), (650, 245), (180, 245)], fill=(64, 53, 49), outline=(130, 97, 72), width=7)
    d.rectangle((160, 150, 210, 425), fill=(50, 35, 30), outline=(110, 76, 51), width=5)
    d.rectangle((620, 150, 670, 425), fill=(50, 35, 30), outline=(110, 76, 51), width=5)
    d.rectangle((735, 100, 895, 335), fill=(23, 30, 34), outline=(112, 82, 60), width=8)
    d.line((815, 100, 815, 335), fill=(110, 80, 60), width=5)
    d.line((735, 220, 895, 220), fill=(110, 80, 60), width=5)
    d.rectangle((85, 310, 170, 405), fill=(52, 36, 29), outline=(107, 75, 52), width=5)
    d.polygon([(105, 290), (150, 290), (165, 330), (90, 330)], fill=(150, 126, 87))
    return im


def scene_chambre_enfant() -> Image.Image:
    im = gradient_background(9)
    d = ImageDraw.Draw(im)
    add_floor(d)
    d.rectangle((100, 255, 440, 400), fill=(44, 34, 38), outline=(111, 81, 65), width=8)
    d.polygon([(125, 220), (400, 220), (440, 275), (100, 275)], fill=(65, 50, 53), outline=(130, 91, 68), width=7)
    d.rectangle((600, 305, 860, 430), fill=(45, 30, 26), outline=(130, 87, 55), width=8)
    d.arc((600, 250, 860, 360), 180, 360, fill=(130, 87, 55), width=8)
    d.rectangle((455, 265, 560, 360), fill=(50, 37, 32), outline=(135, 98, 63), width=7)
    d.ellipse((475, 285, 540, 340), outline=(171, 139, 86), width=7)
    # Dessins d'enfant au mur.
    for x, y in ((220, 90), (420, 130), (700, 100)):
        d.rectangle((x, y, x + 90, y + 90), fill=(66, 58, 49), outline=(132, 105, 72), width=5)
        d.line((x + 12, y + 68, x + 70, y + 20), fill=(160, 125, 85), width=4)
    return im


def scene_salle_de_bain() -> Image.Image:
    im = gradient_background(10)
    d = ImageDraw.Draw(im)
    add_floor(d)
    d.rectangle((340, 70, 620, 260), fill=(23, 31, 34), outline=(135, 107, 83), width=9)
    for offset in range(0, 250, 25):
        d.line((355 + offset, 85, 430 + offset, 245), fill=(55, 66, 69), width=2)
    d.ellipse((160, 285, 760, 500), fill=(52, 55, 54), outline=(143, 123, 101), width=10)
    d.rectangle((190, 350, 730, 450), fill=(33, 35, 35))
    d.line((760, 300, 820, 245), fill=(130, 112, 92), width=10)
    d.arc((790, 205, 860, 285), 180, 360, fill=(130, 112, 92), width=8)
    return im


def scene_grenier() -> Image.Image:
    im = gradient_background(11, horizon=430)
    d = ImageDraw.Draw(im)
    d.polygon([(0, 420), (480, 20), (960, 420)], fill=(41, 29, 25), outline=(112, 75, 49))
    d.polygon([(0, 420), (960, 420), (960, 540), (0, 540)], fill=(29, 22, 20))
    for x in range(80, 900, 150):
        d.line((480, 20, x, 420), fill=(106, 70, 44), width=9)
    d.rectangle((315, 320, 650, 465), fill=(48, 32, 26), outline=(143, 91, 55), width=9)
    d.arc((315, 245, 650, 390), 180, 360, fill=(143, 91, 55), width=9)
    for x, y, w, h in ((90, 350, 130, 95), (705, 315, 150, 130), (145, 250, 110, 80)):
        d.rectangle((x, y, x + w, y + h), fill=(48, 38, 31), outline=(98, 72, 49), width=5)
    return im


def scene_cave() -> Image.Image:
    im = gradient_background(12)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, WIDTH, HEIGHT), fill=(17, 19, 20))
    for x in range(0, WIDTH, 100):
        d.arc((x - 70, 40, x + 160, 330), 180, 360, fill=(60, 57, 52), width=7)
    d.rectangle((650, 140, 895, 430), fill=(25, 23, 24), outline=(93, 82, 67), width=9)
    d.rectangle((705, 190, 840, 365), outline=(65, 61, 55), width=7)
    for x, y in ((90, 310), (210, 330), (330, 300)):
        d.ellipse((x, y, x + 130, y + 160), fill=(44, 33, 27), outline=(105, 78, 54), width=7)
        d.line((x + 10, y + 80, x + 120, y + 80), fill=(120, 87, 58), width=6)
    d.rectangle((420, 300, 580, 400), fill=(45, 44, 40), outline=(112, 107, 91), width=7)
    d.ellipse((450, 325, 500, 375), outline=(157, 145, 115), width=5)
    return im


def scene_atelier() -> Image.Image:
    im = gradient_background(13)
    d = ImageDraw.Draw(im)
    add_floor(d)
    d.rectangle((65, 275, 895, 420), fill=(43, 31, 27), outline=(120, 80, 52), width=9)
    for x in (110, 820):
        d.line((x, 415, x, 525), fill=(71, 48, 35), width=15)
    for x in range(90, 880, 115):
        d.ellipse((x, 110, x + 95, 205), outline=(105, 96, 79), width=9)
        d.ellipse((x + 25, 135, x + 70, 180), outline=(105, 96, 79), width=6)
    d.rectangle((620, 75, 865, 245), fill=(47, 50, 48), outline=(125, 104, 75), width=8)
    d.line((645, 215, 830, 100), fill=(157, 136, 94), width=5)
    d.line((650, 110, 840, 210), fill=(157, 136, 94), width=4)
    return im


def scene_bureau_secret() -> Image.Image:
    im = gradient_background(14)
    d = ImageDraw.Draw(im)
    add_floor(d)
    add_wall_panels(d)
    d.rectangle((180, 295, 650, 430), fill=(44, 28, 24), outline=(135, 89, 55), width=9)
    d.rectangle((225, 235, 590, 320), fill=(65, 54, 41), outline=(150, 120, 75), width=5)
    for x, y in ((245, 250), (350, 245), (475, 260)):
        d.polygon([(x, y), (x + 100, y - 15), (x + 112, y + 35), (x + 10, y + 52)], fill=(150, 137, 103), outline=(95, 78, 54))
    d.rectangle((700, 155, 885, 395), fill=(35, 35, 34), outline=(118, 102, 77), width=10)
    d.ellipse((735, 230, 850, 345), outline=(145, 127, 93), width=7)
    d.ellipse((785, 280, 800, 295), fill=(180, 151, 95))
    return im


def scene_jardin() -> Image.Image:
    im = gradient_background(15, horizon=300)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 300, WIDTH, HEIGHT), fill=(26, 34, 26))
    d.ellipse((350, 320, 610, 560), fill=(42, 32, 26), outline=(70, 58, 39), width=5)
    # Maison au fond.
    d.rectangle((330, 90, 630, 300), fill=(34, 30, 29), outline=(85, 70, 56), width=7)
    d.polygon([(280, 100), (480, 10), (680, 100)], fill=(42, 31, 29), outline=(95, 70, 52))
    for x in (365, 470, 565):
        d.rectangle((x, 145, x + 55, 235), fill=(20, 30, 33), outline=(93, 77, 58), width=5)
    random.seed(15)
    for _ in range(130):
        x = random.randrange(WIDTH)
        base = random.randrange(330, HEIGHT)
        h = random.randrange(20, 100)
        d.line((x, base, x + random.randrange(-15, 16), base - h), fill=(47, 67, 43), width=random.randrange(2, 6))
    d.line((790, 250, 760, 470), fill=(123, 91, 57), width=10)
    d.polygon([(760, 250), (830, 205), (845, 225), (790, 275)], fill=(98, 95, 82))
    return im


def scene_serre() -> Image.Image:
    im = gradient_background(16, horizon=390)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 390, WIDTH, HEIGHT), fill=(27, 39, 29))
    d.arc((100, 45, 860, 730), 180, 360, fill=(137, 146, 128), width=10)
    for x in range(145, 850, 90):
        d.line((480, 45, x, 430), fill=(103, 116, 105), width=5)
    d.line((100, 390, 860, 390), fill=(116, 126, 111), width=8)
    # Quatre jardinières bien distinctes.
    flower_shapes = [(210, 325), (390, 305), (570, 320), (745, 300)]
    for idx, (x, y) in enumerate(flower_shapes):
        d.rectangle((x - 65, 390, x + 65, 465), fill=(57, 39, 27), outline=(118, 80, 48), width=6)
        d.line((x, 390, x, y), fill=(52, 86, 48), width=8)
        petals = 6 + idx
        for p in range(petals):
            angle = p * 2 * math.pi / petals
            px = x + math.cos(angle) * 28
            py = y + math.sin(angle) * 20
            d.ellipse((px - 13, py - 10, px + 13, py + 10), fill=(116 + idx * 12, 86, 76 + idx * 8))
        d.ellipse((x - 12, y - 12, x + 12, y + 12), fill=(170, 145, 84))
    return im


def scene_chapelle() -> Image.Image:
    im = gradient_background(17)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, WIDTH, HEIGHT), fill=(24, 22, 24))
    for x in (80, 310, 540, 770):
        d.line((x, 500, x, 160), fill=(75, 64, 61), width=20)
        d.arc((x - 80, 70, x + 80, 230), 180, 360, fill=(75, 64, 61), width=16)
    d.polygon([(365, 300), (595, 300), (650, 430), (310, 430)], fill=(50, 39, 35), outline=(128, 102, 75), width=8)
    d.rectangle((400, 210, 560, 310), fill=(44, 35, 33), outline=(141, 113, 78), width=7)
    d.ellipse((455, 230, 505, 280), outline=(180, 150, 94), width=7)
    d.rectangle((420, 45, 540, 190), fill=(31, 46, 54), outline=(128, 112, 88), width=8)
    d.line((480, 60, 480, 175), fill=(126, 82, 74), width=8)
    d.line((430, 115, 530, 115), fill=(126, 82, 74), width=8)
    return im


def scene_crypte() -> Image.Image:
    im = gradient_background(18)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, WIDTH, HEIGHT), fill=(13, 16, 17))
    for x in (120, 480, 840):
        d.line((x, 500, x, 175), fill=(64, 65, 61), width=22)
        d.arc((x - 140, 40, x + 140, 320), 180, 360, fill=(64, 65, 61), width=18)
    # Machine centrale.
    d.ellipse((330, 185, 630, 485), fill=(29, 34, 35), outline=(116, 109, 87), width=12)
    d.ellipse((385, 240, 575, 430), outline=(150, 132, 91), width=9)
    for angle in range(0, 360, 30):
        rad = math.radians(angle)
        x1 = 480 + math.cos(rad) * 105
        y1 = 335 + math.sin(rad) * 105
        x2 = 480 + math.cos(rad) * 135
        y2 = 335 + math.sin(rad) * 135
        d.line((x1, y1, x2, y2), fill=(123, 113, 90), width=6)
    d.ellipse((450, 305, 510, 365), fill=(122, 91, 64), outline=(186, 156, 98), width=5)
    d.rectangle((90, 385, 300, 470), fill=(32, 35, 35), outline=(84, 84, 76), width=7)
    d.rectangle((660, 385, 870, 470), fill=(32, 35, 35), outline=(84, 84, 76), width=7)
    return im


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    source = ASSET_DIR / "salon_source.png"
    target = ASSET_DIR / "salon.png"
    if source.exists():
        with Image.open(source) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            img.thumbnail((960, 720), Image.Resampling.LANCZOS)
            img.save(target, optimize=True)

    scenes = {
        "cuisine": scene_cuisine,
        "couloir": scene_couloir,
        "bibliotheque": scene_bibliotheque,
        "salle_a_manger": scene_salle_a_manger,
        "vestibule": scene_vestibule,
        "palier": scene_palier,
        "chambre_maitre": scene_chambre_maitre,
        "chambre_enfant": scene_chambre_enfant,
        "salle_de_bain": scene_salle_de_bain,
        "grenier": scene_grenier,
        "cave": scene_cave,
        "atelier": scene_atelier,
        "bureau_secret": scene_bureau_secret,
        "jardin": scene_jardin,
        "serre": scene_serre,
        "chapelle": scene_chapelle,
        "crypte": scene_crypte,
    }
    for index, (name, builder) in enumerate(scenes.items(), start=20):
        save_scene(name, builder(), index)
        print(f"Créé : assets/rooms/{name}.png")


if __name__ == "__main__":
    main()
