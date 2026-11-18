from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "linkedin"
OUTPUT.mkdir(parents=True, exist_ok=True)

W, H = 1080, 1350
NAVY = (12, 20, 36)
NAVY_2 = (23, 37, 61)
WHITE = (248, 250, 252)
MUTED = (166, 178, 198)
INDIGO = (91, 103, 241)
CYAN = (67, 211, 198)
CORAL = (255, 140, 112)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    candidates = [
        Path("/usr/share/fonts/truetype/dejavu") / name,
        Path("/usr/share/fonts/TTF") / name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def rounded(draw: ImageDraw.ImageDraw, box, radius: int, fill):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def wrapped(draw: ImageDraw.ImageDraw, text: str, position, typeface, fill, max_width: int, spacing: int = 12):
    x, y = position
    words = text.split()
    lines = []
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=typeface)[2] <= max_width:
            line = candidate
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    for index, part in enumerate(lines):
        draw.text((x, y + index * (typeface.size + spacing)), part, font=typeface, fill=fill)
    return y + len(lines) * (typeface.size + spacing)


def base_slide(number: int, accent: tuple[int, int, int] = INDIGO) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (W, H), NAVY)
    draw = ImageDraw.Draw(image)

    draw.ellipse((760, -270, 1220, 190), fill=accent)
    draw.ellipse((820, -210, 1160, 130), fill=NAVY)
    draw.ellipse((-260, 1010, 210, 1480), fill=(23, 37, 61))
    draw.ellipse((-150, 1120, 100, 1370), fill=accent)

    draw.text((86, 86), f"{number:02d} / 05", font=font(20, True), fill=MUTED)
    draw.text((86, 1274), "PFE COPILOT  ·  2026", font=font(16, True), fill=MUTED)
    return image, draw


def save(slide: int, image: Image.Image):
    image.save(OUTPUT / f"slide-{slide}.png", quality=95)


# 1 — Hero
image, draw = base_slide(1, INDIGO)
draw.text((86, 220), "PFE COPILOT", font=font(22, True), fill=(176, 183, 255))
wrapped(draw, "J’ai automatisé\nma recherche de PFE.", (86, 300), font(76, True), WHITE, 820, 18)
draw.text((86, 520), "De l’offre à la candidature.", font=font(28, False), fill=MUTED)
rounded(draw, (86, 650, 994, 1035), 30, NAVY_2)
draw.text((128, 704), "UN PIPELINE COMPLET", font=font(17, True), fill=CYAN)
steps = [
    ("01", "Collecte"),
    ("02", "Matching"),
    ("03", "CV"),
    ("04", "Email"),
    ("05", "Suivi"),
]
for i, (num, label) in enumerate(steps):
    x = 128 + i * 170
    draw.ellipse((x, 790, x + 92, 882), fill=INDIGO if i != 2 else CYAN)
    draw.text((x + 29, 818), num, font=font(18, True), fill=NAVY if i == 2 else WHITE)
    draw.text((x - 4, 914), label, font=font(17, True), fill=WHITE)
    if i < 4:
        draw.line((x + 94, 836, x + 164, 836), fill=(82, 99, 133), width=4)
save(1, image)


# 2 — Problem
image, draw = base_slide(2, CORAL)
draw.text((86, 220), "LE PROBLÈME", font=font(22, True), fill=(255, 174, 153))
wrapped(draw, "Chercher prend\nplus de temps\nque candidater.", (86, 300), font(72, True), WHITE, 820, 18)
rounded(draw, (86, 700, 994, 1120), 28, NAVY_2)
for i, text in enumerate(["Filtrer les offres", "Comparer les profils", "Personnaliser les emails", "Relancer les candidatures"]):
    y = 752 + i * 82
    draw.ellipse((128, y, 158, y + 30), fill=CORAL)
    draw.line((143, y + 30, 143, y + 82), fill=(68, 82, 110), width=3) if i < 3 else None
    draw.text((188, y - 2), text, font=font(25, True), fill=WHITE)
save(2, image)


# 3 — Solution
image, draw = base_slide(3, INDIGO)
draw.text((86, 220), "LA SOLUTION", font=font(22, True), fill=(176, 183, 255))
wrapped(draw, "Un seul pipeline.\nZéro tâche oubliée.", (86, 300), font(70, True), WHITE, 860, 18)
cards = [
    ("COLLECTER", "CSV · RSS · Web · Gmail"),
    ("MATCHER", "Score · Profil · Compétences"),
    ("GÉNÉRER", "CV · Email · Lettre"),
    ("APPROUVER", "Review · Gmail · Suivi"),
]
for i, (title, copy) in enumerate(cards):
    row, col = divmod(i, 2)
    x, y = 86 + col * 468, 700 + row * 230
    rounded(draw, (x, y, x + 430, y + 190), 24, NAVY_2)
    draw.ellipse((x + 28, y + 38, x + 72, y + 82), fill=INDIGO if i != 3 else CYAN)
    draw.text((x + 92, y + 42), title, font=font(24, True), fill=WHITE)
    draw.text((x + 92, y + 86), copy, font=font(16, False), fill=MUTED)
save(3, image)


# 4 — Impact
image, draw = base_slide(4, CYAN)
draw.text((86, 220), "L’IMPACT", font=font(22, True), fill=(125, 235, 223))
wrapped(draw, "Moins d’opérations.\nPlus de contrôle.", (86, 300), font(70, True), WHITE, 860, 18)
metrics = [
    ("4", "profils", INDIGO),
    ("3", "sources", CORAL),
    ("100%", "confirmation", CYAN),
]
for i, (value, label, color) in enumerate(metrics):
    x = 86 + i * 306
    rounded(draw, (x, 700, x + 270, 930), 24, NAVY_2)
    draw.text((x + 30, 750), value, font=font(54, True), fill=color)
    draw.text((x + 30, 835), label, font=font(20, True), fill=WHITE)
rounded(draw, (86, 1000, 882, 1120), 24, (24, 45, 66))
draw.text((120, 1040), "Aucun envoi sans approbation explicite.", font=font(22, True), fill=WHITE)
save(4, image)


# 5 — CTA
image, draw = base_slide(5, INDIGO)
draw.text((86, 220), "LE PROJET", font=font(22, True), fill=(176, 183, 255))
wrapped(draw, "PFE Copilot est\nprêt à évoluer.", (86, 300), font(74, True), WHITE, 860, 18)
rounded(draw, (86, 680, 994, 1040), 28, NAVY_2)
draw.text((128, 730), "STACK", font=font(17, True), fill=CYAN)
stack = ["Python", "Streamlit", "SQLite", "Gmail API", "IA"]
for i, item in enumerate(stack):
    x = 128 + (i % 3) * 280
    y = 790 + (i // 3) * 100
    rounded(draw, (x, y, x + 250, y + 66), 33, INDIGO if i < 3 else CORAL)
    draw.text((x + 24, y + 20), item, font=font(18, True), fill=WHITE)
draw.text((86, 1180), "Merci pour votre attention.", font=font(28, True), fill=WHITE)
save(5, image)

print(f"Generated 5 LinkedIn slides in {OUTPUT}")
