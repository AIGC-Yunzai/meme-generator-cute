"""测量表情包气泡内的可用文字范围。

表情包素材大多是「白色气泡 + 深色描边」的样式，`draw_text` 需要传入一个矩形范围。
手工量容易偏，这个脚本用洪水填充把气泡内部圈出来，给出气泡外接框，
再按比例推荐一个留了内边距的文字范围。

用法::

    python tools/measure_bubble.py memes/deepSeekThink/images/DSniangThink.png

气泡是「封闭图形」才能填充成功，所以需要给一个位于气泡内部的种子点。
默认种子点取图片左上区域 (45%, 25%)，大多数这类素材都适用；
如果气泡不在左上，用 ``--seed 500,300``（像素坐标）指定。

不依赖项目运行环境，只需要 Pillow。
"""

from __future__ import annotations

import argparse
import sys
from collections import deque
from pathlib import Path

from PIL import Image

# 认为是「描边/前景」的判定：alpha 很低视为透明，其余为深色或高饱和
ALPHA_MIN = 180
DARK_MAX = 200
SAT_MAX = 40

# 文字范围相对气泡外接框的内缩比例（沿用了仓库已有表情的实测经验值）
PAD_X_RATIO = 0.115
PAD_TOP_RATIO = 0.135
PAD_BOTTOM_RATIO = 0.055

# 气泡底部一般还有一条细尾巴（指向角色），尾巴宽度远小于主体。
# 低于「最宽处 * 该比例」的行视为尾巴，不参与文字范围计算。
TAIL_WIDTH_RATIO = 0.5


def build_barrier(px, w: int, h: int, dilate: int = 1) -> set[tuple[int, int]]:
    """返回描边像素集合（做一次膨胀，避免抗锯齿造成的缝隙漏填充）。"""
    base: set[tuple[int, int]] = set()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < ALPHA_MIN:
                continue
            if max(r, g, b) < DARK_MAX or (max(r, g, b) - min(r, g, b)) > SAT_MAX:
                base.add((x, y))

    if dilate <= 0:
        return base

    grown: set[tuple[int, int]] = set()
    for x, y in base:
        for dx in range(-dilate, dilate + 1):
            for dy in range(-dilate, dilate + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    grown.add((nx, ny))
    return grown


def flood_bubble_interior(
    px, w: int, h: int, seed: tuple[int, int], barrier: set[tuple[int, int]]
) -> dict:
    """从 seed 出发填充气泡内部（被描边挡住），返回外接框与逐行左右边界。"""
    sx, sy = seed
    if not (0 <= sx < w and 0 <= sy < h):
        raise SystemExit(
            f"种子点 {seed} 超出图片范围（图片 {w} x {h}）。"
            f"坐标应满足 0 <= x < {w}、0 <= y < {h}"
        )
    if seed in barrier:
        raise SystemExit(
            f"种子点 {seed} 落在了描边上，请换一个气泡内部的点（--seed x,y）"
        )

    seen = {seed}
    queue = deque([seed])
    min_x = max_x = seed[0]
    min_y = max_y = seed[1]
    rows: dict[int, list[int]] = {}
    count = 0

    while queue:
        x, y = queue.popleft()
        count += 1
        min_x, max_x = min(min_x, x), max(max_x, x)
        min_y, max_y = min(min_y, y), max(max_y, y)
        if y in rows:
            rows[y][0] = min(rows[y][0], x)
            rows[y][1] = max(rows[y][1], x)
        else:
            rows[y] = [x, x]

        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and (nx, ny) not in barrier:
                seen.add((nx, ny))
                queue.append((nx, ny))

    # 漏填检测：种子点若落在气泡外的透明区域（或描边有缺口），洪水会灌满整片背景
    # 并一路漫到图片四边。这时脚本会认真输出一个巨大的外接框和「建议文字范围」，
    # 看起来像是成功了 —— 比直接报错危险得多。
    if min_x == 0 or min_y == 0 or max_x == w - 1 or max_y == h - 1:
        raise SystemExit(
            f"填充区域触及了图片边界（外接框 ({min_x}, {min_y}, {max_x}, {max_y})，"
            f"共 {count} px）。\n"
            "种子点很可能不在**封闭的气泡内部**：要么点在气泡外的透明区域，\n"
            "要么气泡描边有缺口导致漏填充。请换一个确实落在气泡内部、"
            "且不在描边上的点：--seed x,y"
        )

    return {
        "count": count,
        "min_x": min_x,
        "max_x": max_x,
        "min_y": min_y,
        "max_y": max_y,
        "rows": rows,
    }


def body_bottom(bbox: dict) -> int:
    """气泡主体底边：排除底部细尾巴后，得到最后一行"够宽"的 y。"""
    rows = bbox["rows"]
    max_width = max(right - left for left, right in rows.values())
    threshold = max_width * TAIL_WIDTH_RATIO
    for y in sorted(rows, reverse=True):
        left, right = rows[y]
        if right - left >= threshold:
            return y
    return bbox["max_y"]


def suggest_text_box(bbox: dict) -> tuple[int, int, int, int]:
    """由气泡外接框按内缩比例给出建议文字范围，并取整到 5 的倍数。"""
    min_x, max_x = bbox["min_x"], bbox["max_x"]
    min_y, max_y = bbox["min_y"], body_bottom(bbox)
    width, height = max_x - min_x, max_y - min_y

    left = min_x + round(width * PAD_X_RATIO)
    right = max_x - round(width * PAD_X_RATIO)
    top = min_y + round(height * PAD_TOP_RATIO)
    bottom = max_y - round(height * PAD_BOTTOM_RATIO)

    round5 = lambda v: int(round(v / 5) * 5)  # noqa: E731
    return round5(left), round5(top), round5(right), round5(bottom)


def main() -> None:
    parser = argparse.ArgumentParser(description="测量表情包气泡内可用文字范围")
    parser.add_argument("image", type=Path, help="素材图片路径")
    parser.add_argument(
        "--seed",
        default=None,
        help="气泡内部的种子点，形如 450,250（像素坐标）。默认取 (45%, 25%)",
    )
    parser.add_argument("--dilate", type=int, default=1, help="描边膨胀像素，默认 1")
    args = parser.parse_args()

    image = Image.open(args.image).convert("RGBA")
    w, h = image.size
    px = image.load()

    # Windows 控制台默认不是 UTF-8，直接输出中文会乱码
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if args.seed:
        sx, sy = (int(v) for v in args.seed.split(","))
    else:
        sx, sy = int(w * 0.45), int(h * 0.25)

    barrier = build_barrier(px, w, h, args.dilate)
    bbox = flood_bubble_interior(px, w, h, (sx, sy), barrier)
    box = suggest_text_box(bbox)

    print(f"图片      : {args.image}  ({w} x {h})")
    print(f"种子点    : ({sx}, {sy})")
    print(f"气泡面积  : {bbox['count']} px")
    print(
        "气泡外接框: "
        f"({bbox['min_x']}, {bbox['min_y']}, {bbox['max_x']}, {bbox['max_y']})  "
        f"宽 {bbox['max_x'] - bbox['min_x']} 高 {bbox['max_y'] - bbox['min_y']}"
    )
    print(
        "归一化    : "
        f"x {bbox['min_x'] / w:.3f}..{bbox['max_x'] / w:.3f}  "
        f"y {bbox['min_y'] / h:.3f}..{bbox['max_y'] / h:.3f}"
    )
    print(f"主体底边  : {body_bottom(bbox)}（已排除底部细尾巴）")
    print()
    print(f"建议文字范围: {box}")
    print("  draw_text({}, text, ...)".format(box))
    print()
    ys = sorted(bbox["rows"])
    step = max(1, len(ys) // 24)
    n_samples = len(ys[::step])
    print(f"逐行左右边界（约 {n_samples} 个采样点，y: left..right）：")
    for y in ys[::step]:
        left, right = bbox["rows"][y]
        print(f"  y={y:>5} ({y / h:.3f})  x {left:>5}..{right:<5}  宽 {right - left}")


if __name__ == "__main__":
    main()
