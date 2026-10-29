import random
from datetime import datetime
from pathlib import Path

from pil_utils import BuildImage
from pydantic import Field

from meme_generator import (
    MemeArgsModel,
    MemeArgsType,
    ParserArg,
    ParserOption,
    add_meme,
)
from meme_generator.exception import MemeFeedback, TextOverLength

img_dir = Path(__file__).parent / "images"

DEFAULT_TEXT = "老实赚钱，很枯燥吧"
TOTAL_NUM = 3
help_text = f"图片编号，范围为 1~{TOTAL_NUM}，0 表示随机"

# 素材 1672x941。参考帧（1920x1080）里中文那行墨迹在 y 922..964、x 743..1176，
# 水平中心与图宽中心重合；按 0.871 折算到本素材是 y 803..840，中心 821。
# 字幕区以该行为垂直中心，宽度取画面的 70%（真实字幕一行不会铺满整幅宽），
# 高度按 44px 字号两行排版（约 116px）留量，折行时上下扩展而不是一路向下。
# 换素材必须重新量，这组数字来自这一帧的具体构图（见 docs/adr/0001）。
SUBTITLE_AREA = (251, 760, 1421, 884)
SUBTITLE_FONT_MAX = 44
SUBTITLE_FONT_MIN = 26
# 参考帧描边约 3~4px / 字号约 50px，折算到 44px 字号约 0.07
SUBTITLE_STROKE_RATIO = 0.07


class Model(MemeArgsModel):
    number: int = Field(0, description=help_text)


args_type = MemeArgsType(
    args_model=Model,
    parser_options=[
        ParserOption(
            names=["-n", "--number"],
            args=[ParserArg(name="number", value="int")],
            help_text=help_text,
        ),
    ],
)


def honest_money(images, texts: list[str], args: Model):
    text = texts[0]
    if args.number == 0:
        num = random.randint(1, TOTAL_NUM)
    elif 1 <= args.number <= TOTAL_NUM:
        num = args.number
    else:
        raise MemeFeedback(f"图片编号错误，请选择 1~{TOTAL_NUM}")

    frame = BuildImage.open(img_dir / f"{num:02d}.png")
    try:
        frame.draw_text(
            SUBTITLE_AREA,
            text,
            max_fontsize=SUBTITLE_FONT_MAX,
            min_fontsize=SUBTITLE_FONT_MIN,
            allow_wrap=True,
            lines_align="center",
            fill="white",
            stroke_ratio=SUBTITLE_STROKE_RATIO,
            stroke_fill="black",
        )
    except ValueError:
        raise TextOverLength(text)
    return frame.save_png()


add_meme(
    "honest_money",
    honest_money,
    min_texts=1,
    max_texts=1,
    default_texts=[DEFAULT_TEXT],
    args_type=args_type,
    keywords=["老实赚钱", "老实赚钱很枯燥吧"],
    tags={"久留美", "deepseek娘", "小呆毛"},
    date_created=datetime(2026, 10, 29),
    date_modified=datetime(2026, 10, 29),
)
