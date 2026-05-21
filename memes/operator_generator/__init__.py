import random
from datetime import datetime
from pathlib import Path

from pil_utils import BuildImage

from meme_generator import add_meme
from meme_generator.exception import TextOverLength

img_dir = Path(__file__).parent / "images"

CATEGORIES = ("range", "characteristic", "value", "talent", "skill", "special")
POSITIONS = {
    "range": (0, 100),
    "characteristic": (320, 100),
    "value": (0, 280),
    "talent": (320, 280),
    "skill": (0, 460),
    "special": (320, 460),
}


def operator_generator(images: list[BuildImage], texts, args):
    avatar = images[0].convert("RGBA").circle().resize((80, 80), keep_ratio=False)
    name = args.user_infos[0].name if args.user_infos else "你"
    banner = f"{name}，你的干员信息如下："

    frame = BuildImage.new("RGBA", (640, 640), (160, 160, 160))
    frame.paste(avatar, (20, 10), alpha=True)
    try:
        frame.draw_text(
            (120, 0, 620, 100),
            banner,
            min_fontsize=30,
            max_fontsize=80,
            fill="white",
            stroke_fill="black",
            stroke_ratio=0.05,
        )
    except ValueError:
        raise TextOverLength(name)

    for category in CATEGORIES:
        card = BuildImage.open(
            img_dir / category / f"{random.randint(0, 24):02d}.jpg"
        ).resize_width(320)
        frame.paste(card, POSITIONS[category])

    return frame.save_png()


add_meme(
    "operator_generator",
    operator_generator,
    min_images=1,
    max_images=1,
    keywords=["合成大干员"],
    tags={"明日方舟"},
    date_created=datetime(2023, 3, 28),
    date_modified=datetime(2023, 3, 28),
)
