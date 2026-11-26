"""Copertine originali delle basi Killa On The Beat (3000x3000)."""
import math, os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = 3000
OUT = os.path.join(os.path.dirname(__file__), "copertine")
os.makedirs(OUT, exist_ok=True)
F = "/usr/share/fonts/truetype/google-fonts/ofl/"
ANTON = F + "anton/Anton-Regular.ttf"
MONT = F + "montserrat/Montserrat[wght].ttf"

yy, xx = np.mgrid[0:S, 0:S].astype(np.float32) / S


def mix(c1, c2, t):
    t = np.clip(t, 0, 1)[..., None]
    return np.array(c1, np.float32) * (1 - t) + np.array(c2, np.float32) * t


def to_img(a):
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


def glow(img, draw_fn, radius, alpha=1.0):
    layer = Image.new("RGB", (S, S), 0)
    draw_fn(ImageDraw.Draw(layer))
    blurred = layer.filter(ImageFilter.GaussianBlur(radius))
    a = np.asarray(img, np.float32) + (np.asarray(blurred, np.float32) * alpha) + np.asarray(layer, np.float32) * 0.6
    return to_img(a)


def font(path, size, wght=None):
    f = ImageFont.truetype(path, size)
    if wght:
        try:
            f.set_variation_by_axes([wght])
        except Exception:
            pass
    return f


def testi(img, titolo, info, colore=(255, 255, 255), accento=(255, 200, 80)):
    d = ImageDraw.Draw(img)
    # scurisce il fondo in basso per leggere bene
    sh = Image.new("L", (S, S), 0)
    ImageDraw.Draw(sh).rectangle([0, int(S * 0.62), S, S], fill=170)
    sh = sh.filter(ImageFilter.GaussianBlur(220))
    img.paste(Image.new("RGB", (S, S), 0), (0, 0), sh)
    d = ImageDraw.Draw(img)
    fk = font(MONT, 118, 800)
    d.text((S // 2, 230), "KILLA ON THE BEAT", font=fk, fill=accento, anchor="mm")
    # titolo: rimpicciolisce finché sta nella larghezza
    size = 520
    righe = titolo.upper().split("\n")
    while True:
        ft = font(ANTON, size)
        if max(d.textlength(r, font=ft) for r in righe) <= S * 0.86:
            break
        size -= 10
    h = size * 1.08
    y0 = S * 0.80 - 60 - h * (len(righe) - 1)
    for i, r in enumerate(righe):
        d.text((S // 2, y0 + i * h), r, font=ft, fill=colore, anchor="mm")
    fi = font(MONT, 96, 600)
    d.text((S // 2, S - 210), info, font=fi, fill=(235, 235, 235), anchor="mm")
    return img


def salva(img, nome):
    img.save(os.path.join(OUT, nome + ".jpg"), quality=92)
    img.resize((900, 900), Image.LANCZOS).save(os.path.join(OUT, nome + "_900.jpg"), quality=88)


rng = random.Random(7)

# 1. Dalla Polvere: polvere e braci che salgono
a = mix((20, 14, 12), (95, 40, 15), (1 - yy) ** 0.2 * 0 + yy ** 1.5)
img = to_img(a)
def braci(d):
    for _ in range(900):
        x, y = rng.uniform(0, S), rng.uniform(S * 0.15, S)
        r = rng.uniform(3, 14) * (y / S)
        c = (255, rng.randint(90, 170), 30)
        d.ellipse([x - r, y - r, x + r, y + r], fill=c)
img = glow(img, braci, 18, 1.4)
def fumo(d):
    for _ in range(40):
        x, y = rng.uniform(0, S), rng.uniform(S * 0.5, S)
        r = rng.uniform(150, 400)
        d.ellipse([x - r, y - r * .5, x + r, y + r * .5], fill=(60, 45, 38))
pass
salva(testi(img, "Dalla Polvere", "TRAP-METAL · 150 BPM · RE MINORE", accento=(255, 150, 50)), "01_dalla_polvere")

# 2. Night Instrumental: notte blu, luna, tasti di pianoforte
d2 = np.hypot(xx - 0.72, yy - 0.24)
a = mix((8, 12, 35), (25, 45, 95), 1 - yy) + (np.exp(-(d2 / 0.18) ** 2) * 60)[..., None]
img = to_img(a)
def stelle(d):
    for _ in range(500):
        x, y, r = rng.uniform(0, S), rng.uniform(0, S * 0.6), rng.uniform(1.5, 5)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(220, 230, 255))
    d.ellipse([S * .72 - 210, S * .24 - 210, S * .72 + 210, S * .24 + 210], fill=(235, 238, 255))
img = glow(img, stelle, 40, 0.9)
d = ImageDraw.Draw(img)
ytop = int(S * 0.40)
w = S / 26
for i in range(26):
    d.rectangle([i * w + 4, ytop, (i + 1) * w - 4, ytop + 260], fill=(200, 210, 235))
for i in range(26):
    if i % 7 not in (2, 6):
        d.rectangle([i * w + w * .65, ytop, i * w + w * 1.35, ytop + 160], fill=(10, 14, 35))
salva(testi(img, "Night\nInstrumental", "TRAP MELODICA · 140 BPM · LA MINORE", accento=(160, 190, 255)), "02_night_instrumental")

# 3. Sole d'Africa: grande sole e raggi
ang = np.arctan2(yy - 0.42, xx - 0.5)
rd = np.hypot(xx - 0.5, yy - 0.42)
raggi = (np.sin(ang * 18) > 0.3).astype(np.float32) * np.exp(-rd * 1.5) * 0.35
a = mix((120, 25, 10), (250, 150, 30), 1 - yy * 0.9) + (raggi * 120)[..., None]
img = to_img(a)
def sole(d):
    r = 430
    d.ellipse([S / 2 - r, S * .42 - r, S / 2 + r, S * .42 + r], fill=(255, 225, 120))
img = glow(img, sole, 120, 1.0)
d = ImageDraw.Draw(img)
pts = [(0, S)] + [(x, S * 0.62 - 140 * math.sin(x / S * math.pi * 2.3) - 90 * math.sin(x / S * 11)) for x in range(0, S + 1, 30)] + [(S, S)]
d.polygon(pts, fill=(45, 15, 8))
for tx, th in ((520, 520), (2350, 620)):  # due acacie stilizzate
    d.rectangle([tx - 14, S * .62 - th + 200, tx + 14, S * .66], fill=(30, 10, 5))
    d.ellipse([tx - 280, S * .62 - th + 120, tx + 280, S * .62 - th + 260], fill=(30, 10, 5))
salva(testi(img, "Sole d'Africa", "AFROBEAT · REGGAE · 105 BPM · SOL MAGGIORE", accento=(255, 230, 140)), "03_sole_dafrica")

# 4. Re senza corona: corona dorata spezzata su viola scuro
a = mix((10, 5, 18), (60, 20, 70), np.exp(-(np.hypot(xx - .5, yy - .38) / .45) ** 2))
img = to_img(a)
def corona(d):
    cx, cy, w, h = S / 2, S * .40, 1150, 640
    pts = [(cx - w / 2, cy + h / 2), (cx - w / 2, cy - h / 3), (cx - w / 4, cy + h / 10), (cx, cy - h / 2),
           (cx + w / 4, cy + h / 10), (cx + w / 2, cy - h / 3), (cx + w / 2, cy + h / 2)]
    d.polygon(pts, fill=(230, 175, 50))
    d.rectangle([cx - w / 2, cy + h / 2 - 110, cx + w / 2, cy + h / 2], fill=(200, 145, 35))
    for px, py in pts[1:6:2] + [pts[3]]:
        d.ellipse([px - 50, py - 50, px + 50, py + 50], fill=(255, 225, 130))
    crepa = [(cx + 40, cy - h / 2 + 40), (cx - 30, cy - 60), (cx + 50, cy + 60), (cx - 20, cy + h / 2 + 5)]
    d.line(crepa, fill=(20, 8, 25), width=34, joint="curve")
img = glow(img, corona, 90, 0.8)
salva(testi(img, "Re senza corona", "TRAP CINEMATOGRAFICA · 145 BPM · DO MINORE", accento=(240, 190, 70)), "04_re_senza_corona")

# 5. Respiro: nebbia verde-azzurra e cerchi morbidi
a = mix((18, 40, 45), (95, 130, 130), 1 - np.hypot(xx - .5, yy - .4) * 1.4)
img = to_img(a)
def cerchi(d):
    for i in range(7):
        r = 180 + i * 150
        d.ellipse([S / 2 - r, S * .4 - r, S / 2 + r, S * .4 + r], outline=(200, 235, 230), width=6)
img = glow(img, cerchi, 30, 0.7)
img = img.filter(ImageFilter.GaussianBlur(2))
salva(testi(img, "Respiro", "RAP MELODICO · LO-FI · 86 BPM · RE MAGGIORE", accento=(190, 240, 230)), "05_respiro")

# 6. Corri: linee di velocità rosso neon
a = mix((8, 0, 4), (40, 0, 12), xx)
img = to_img(a)
def linee(d):
    for _ in range(140):
        y = rng.uniform(S * .2, S * .66)
        x = rng.uniform(-S * .2, S * .9)
        l = rng.uniform(300, 1400)
        c = rng.choice([(255, 30, 60), (255, 80, 40), (255, 255, 255)])
        d.line([x, y, x + l, y - l * .12], fill=c, width=rng.randint(4, 16))
img = glow(img, linee, 25, 1.3)
salva(testi(img, "Corri", "RAGE TRAP · 161 BPM · FA MINORE", accento=(255, 60, 80)), "06_corri")

# 7. Mare Calmo: onde turchesi
a = mix((5, 40, 70), (20, 160, 170), 1 - yy)
img = to_img(a)
d = ImageDraw.Draw(img)
for k in range(22):
    y0 = S * .36 + k * 62
    pts = [(x, y0 + 30 * math.sin(x / S * 9 + k * .7) + 15 * math.sin(x / S * 23)) for x in range(0, S + 1, 20)]
    shade = int(230 - k * 7)
    d.line(pts, fill=(shade, 250, 245), width=5)
img = glow(img, lambda dd: dd.ellipse([S * .5 - 220, S * .27 - 220, S * .5 + 220, S * .27 + 220], fill=(255, 240, 200)), 100, 0.8)
salva(testi(img, "Mare Calmo", "AFRO-TRAP · 99 BPM · SI MINORE", accento=(200, 255, 245)), "07_mare_calmo")

# 8. Believe: fascio di luce dall'alto su nero, coro di raggi
ang = np.arctan2(xx - .5, yy + .05)
fascio = np.exp(-(ang / 0.22) ** 2) * (1 - yy * 0.6)
a = mix((5, 5, 8), (255, 215, 140), fascio * .75)
img = to_img(a)
def polvere(d):
    for _ in range(700):
        y = rng.uniform(S * .05, S * .75)
        spread = 0.22 * (y / S + .05) * S * 1.1
        x = S / 2 + rng.gauss(0, spread * .45)
        r = rng.uniform(2, 7)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 235, 190))
img = glow(img, polvere, 10, 1.0)
salva(testi(img, "Believe", "UK DRILL · 144 BPM · RE MINORE", accento=(255, 215, 140)), "08_believe")
print("fatto")
