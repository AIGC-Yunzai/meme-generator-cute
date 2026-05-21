import math
from datetime import datetime
from pathlib import Path

from pil_utils import BuildImage

from meme_generator import add_meme
from meme_generator.utils import make_png_or_gif

img_dir = Path(__file__).parent / "images"


def cover_to_size(img: BuildImage, size: tuple[int, int]) -> BuildImage:
    img = img.convert("RGBA")
    scale = max(size[0] / img.width, size[1] / img.height)
    resized = img.resize(
        (math.ceil(img.width * scale), math.ceil(img.height * scale)),
        keep_ratio=False,
    )
    left = max((resized.width - size[0]) // 2, 0)
    top = max((resized.height - size[1]) // 2, 0)
    return resized.crop((left, top, left + size[0], top + size[1]))


def forbid(images: list[BuildImage], texts, args):
    frame = BuildImage.open(img_dir / "0.png")
    size = frame.size

    def make(imgs: list[BuildImage]) -> BuildImage:
        base = cover_to_size(imgs[0], size)
        return base.paste(frame, (0, 0), alpha=True)

    return make_png_or_gif(images, make)


add_meme(
    "forbid",
    forbid,
    min_images=1,
    max_images=1,
    keywords=["禁止", "禁"],
    date_created=datetime(2023, 3, 12),
    date_modified=datetime(2023, 3, 12),
)
