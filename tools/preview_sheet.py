"""把多张图竖着拼成一张对比图：看多个版本时只读一次图。

用法::

    # 三张成品拼一张
    python tools/preview_sheet.py tools/out/a.png tools/out/b.png tools/out/c.png

    # 指定输出与缩放宽度（默认 900，够看清字幕）
    python tools/preview_sheet.py tools/out/*.png -o tools/out/sheet.png --width 1200

为什么要有这个脚本：逐张读图既慢又难比较——字号差 4px、描边差 1px，单看一张看不出来，
并排才看得出来。图多的时候拼一张，读图成本从 N 次降到 1 次。

每张图左上角会标序号，脚本同时把「序号 → 文件」打到终端，对照着看。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO_ROOT / "tools" / "out" / "sheet.png"
DEFAULT_WIDTH = 900
DEFAULT_GAP = 6


def load_scaled(path: Path, width: int) -> Image.Image:
    img = Image.open(path).convert("RGB")
    if img.width != width:
        height = max(1, round(img.height * width / img.width))
        img = img.resize((width, height), Image.LANCZOS)
    return img


def build_sheet(paths: list[Path], width: int, gap: int) -> Image.Image:
    imgs = [load_scaled(p, width) for p in paths]
    total_h = sum(i.height for i in imgs) + gap * (len(imgs) - 1)
    sheet = Image.new("RGB", (width, total_h), (32, 32, 32))
    draw = ImageDraw.Draw(sheet)

    y = 0
    for idx, img in enumerate(imgs, 1):
        sheet.paste(img, (0, y))
        # 序号写在左上角，黑底白字，深色浅色素材上都看得见
        draw.rectangle((0, y, 34, y + 26), fill=(0, 0, 0))
        draw.text((10, y + 7), str(idx), fill=(255, 255, 255))
        y += img.height + gap

    return sheet


def main() -> None:
    parser = argparse.ArgumentParser(description="把多张图竖着拼成一张对比图")
    parser.add_argument("images", nargs="+", type=Path, help="要拼的图片，按传入顺序自上而下")
    parser.add_argument("-o", "--out", type=Path, default=DEFAULT_OUT, help="输出路径")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH, help=f"每张缩放到这个宽度，默认 {DEFAULT_WIDTH}")
    parser.add_argument("--gap", type=int, default=DEFAULT_GAP, help=f"图之间的间隔像素，默认 {DEFAULT_GAP}")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows 控制台默认不是 UTF-8

    missing = [p for p in args.images if not p.is_file()]
    if missing:
        sys.exit("找不到图片：\n  " + "\n  ".join(str(p) for p in missing))

    sheet = build_sheet(args.images, args.width, args.gap)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)

    print("序号 → 文件")
    for idx, path in enumerate(args.images, 1):
        print(f"  {idx} → {path}")
    print()
    print(f"已写入: {args.out.resolve()}")
    print(f"尺寸  : {sheet.width}×{sheet.height}（{len(args.images)} 张，每张宽 {args.width}）")


if __name__ == "__main__":
    main()
