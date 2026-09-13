"""用 meme_generator 渲染本仓库的表情，并把产物路径打出来。

这是「本地预览」入口：把 ``memes/`` 目录注册进 meme_generator，
然后调用指定表情的生成函数，把 PNG 落到 ``tools/out/``。

用法::

    # 用表情自带的默认文字
    python tools/render_meme.py

    # 指定表情与文字
    python tools/render_meme.py -m deep_seek_think -t "深度思考中"

    # 渲染完直接打开图片
    python tools/render_meme.py -t "在吗" --open

    # 换个输出目录 / 换个文件名
    python tools/render_meme.py -o D:/tmp -n preview.png

    # 列出本仓库表情，并做冲突自检（有问题退出码非 0，可直接进 CI）
    python tools/render_meme.py --list

依赖（装在隔离 venv 里，不要污染系统 Python）::

    python -m venv <venv>
    <venv>/Scripts/python.exe -m pip install "meme_generator<0.2.0" filetype pillow

注意：Windows 上 skia 会打印 ``SkIcuLoader: datafile missing`` 告警，
不影响中文渲染（走系统字体），可以忽略。
"""

from __future__ import annotations

import argparse
import ast
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MEMES_DIR = REPO_ROOT / "memes"
DEFAULT_OUT_DIR = REPO_ROOT / "tools" / "out"
DEFAULT_MEME = "deep_seek_think"


def iter_meme_dirs(memes_dir: Path) -> list[Path]:
    """memes/ 下的所有表情目录（排除 __pycache__ 等以 _ 开头的目录）。

    注意是按「目录」发现，**不要求**目录里已经有 __init__.py —— 这样漏建
    __init__.py 的新目录也能被 --list 看到（并报「缺少 __init__.py」），
    而不是静默漏掉、最终「检查通过」。
    """
    return sorted(
        p for p in memes_dir.iterdir() if p.is_dir() and not p.name.startswith("_")
    )


def scan_static(
    memes_dir: Path,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]], list[str]]:
    """静态扫描 memes/*/__init__.py，提取 add_meme 的 meme key 与 keywords。

    只解析 AST，**不执行模块**，所以无依赖也能跑。返回
    ``(keys, keywords, blockers)``，前两项元素为 ``(值, 相对路径)``。

    两类的性质完全不同，所以分开收集、分开报：

    - **meme key** 是上游注册表 ``manager._memes`` 的键。重复时 ``add_meme``
      只 warning 后 ``return``，**保留先注册的、丢弃后注册的**。
    - **keywords** 在本包里只是 ``Meme`` 的元数据（``cli.py`` 只拿它当
      ``help_text``），本包内重复不会冲突；真正拿它当触发词的是消费端适配器，
      所以重复的后果取决于适配器，仍应避免。

    ``blockers`` 覆盖四种「会让 --list 假绿」的情况，都算硬错而非提示：

    - 目录缺 ``__init__.py``（否则既不进静态扫描也不进 expected，整条漏掉）；
    - 顶层 ``add_meme`` 不是 1 处；
    - ``add_meme`` 不是模块最后一条顶层语句 —— 否则「先注册成功、后面再 raise」
      会让模块其实没导入成功，但 key 已经进了注册表，``--list`` 假绿；
    - key / keywords 没法静态解析（写成模块常量之类），或 keywords 为空。
    """
    keys: list[tuple[str, str]] = []
    keywords: list[tuple[str, str]] = []
    blockers: list[str] = []

    for meme_dir in iter_meme_dirs(memes_dir):
        path = meme_dir / "__init__.py"
        dir_rel = meme_dir.relative_to(memes_dir.parent).as_posix()  # 如 memes/foo
        if not path.is_file():
            blockers.append(f"{dir_rel}: 缺少 __init__.py（这个目录不会注册任何表情）")
            continue
        rel = path.relative_to(memes_dir.parent).as_posix()

        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as e:
            blockers.append(f"{rel}: 语法错误，无法解析（{e.msg}，第 {e.lineno} 行）")
            continue

        # 只看顶层 add_meme 调用：模块 import 时执行的正是这些
        top_calls = [
            (i, stmt.value)
            for i, stmt in enumerate(tree.body)
            if isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Call)
            and getattr(stmt.value.func, "id", "") == "add_meme"
        ]
        if len(top_calls) != 1:
            blockers.append(
                f"{rel}: 顶层有 {len(top_calls)} 处 add_meme，"
                "本仓库约定一个目录恰好注册一个表情"
            )
            if not top_calls:
                continue

        idx, node = top_calls[0]
        if idx != len(tree.body) - 1:
            blockers.append(
                f"{rel}: add_meme 不是模块最后一条语句。本仓库约定它必须放在最后 —— "
                "否则「先注册成功、后面再 raise」会让模块其实没导入成功，"
                "但 key 已经进了注册表，--list 会假绿。"
            )

        if (
            node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            keys.append((node.args[0].value, rel))
        else:
            blockers.append(
                f"{rel}: 无法静态解析 add_meme 的 key（必须写成字符串字面量）"
            )

        kw_values = [kw for kw in node.keywords if kw.arg == "keywords"]
        if not kw_values:
            blockers.append(f"{rel}: 找不到 keywords=（本仓库约定每个表情都要有触发词）")
            continue
        for kw in kw_values:
            if not isinstance(kw.value, ast.List):
                blockers.append(
                    f"{rel}: 无法静态解析 keywords（必须写成列表字面量，"
                    "否则重复检测会静默失效）"
                )
                continue
            if not kw.value.elts:
                blockers.append(f"{rel}: keywords 不能为空（本仓库约定每个表情都要有触发词）")
                continue
            for elt in kw.value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    keywords.append((elt.value, rel))
                else:
                    blockers.append(
                        f"{rel}: keywords 里有非字符串字面量元素，重复检测会漏掉它"
                    )

    return keys, keywords, blockers


def find_duplicates(pairs: list[tuple[str, str]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for value, src in pairs:
        grouped.setdefault(value, []).append(src)
    return {v: srcs for v, srcs in grouped.items() if len(srcs) > 1}


def load_repo_memes() -> tuple[list[str], list[str]]:
    """把本仓库 memes/ 下的表情注册进 meme_generator。

    返回 ``(本仓库注册成功的 key, memes/ 下的目录名)``。

    两个坑决定了这里要自己复查一遍：
    1. ``meme_generator`` 被 import 时会先加载它自带的近 300 个内置表情，
       所以 ``get_meme_keys()`` 是全量，必须取「注册前后的差集」才是本仓库的。
    2. ``load_memes`` 会把导入异常 catch 掉只写日志；``add_meme`` 遇到重复 key
       也只 warning 后直接 return。两者都是静默失败，不复查就会把
       「表情压根没注册上」误报成「key 写错了」。

    这里**只**返回 ``(registered, expected)``，不做任何提前退出 ——
    哪怕一个都没注册成功，也交给 :func:`report_check` 把「静态扫到了但没注册成功」
    的完整诊断打出来，而不是在这里用一句笼统的提示把后续诊断跳掉。
    """
    try:
        from meme_generator import get_meme_keys, load_memes
    except ImportError as e:
        sys.exit(
            f"导入 meme_generator 失败：{e}\n"
            "请用装了依赖的 venv 解释器运行本脚本，例如：\n"
            "  <venv>/Scripts/python.exe tools/render_meme.py"
        )

    if not MEMES_DIR.is_dir():
        sys.exit(f"找不到表情目录：{MEMES_DIR}")

    # 按目录计数（不要求 __init__.py 存在）：漏建 __init__.py 的目录也进 expected，
    # 这样「目录数 vs 注册数」和静态 blocker 才能照出它。
    expected = sorted(p.name for p in iter_meme_dirs(MEMES_DIR))

    before = set(get_meme_keys())
    load_memes(MEMES_DIR)
    registered = sorted(set(get_meme_keys()) - before)

    return registered, expected


def open_file(path: Path) -> None:
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=True)
        else:
            subprocess.run(["xdg-open", str(path)], check=True)
        print("已用系统默认程序打开。")
    except Exception as e:  # noqa: BLE001
        print(f"打开失败（{type(e).__name__}: {e}），请手动打开上面的路径。")


def report_check(registered: list[str], expected_dirs: list[str]) -> int:
    """``--list``：列表情 + 做两类冲突检查，返回进程退出码（有问题非 0）。

    退出码非 0 是刻意的 —— 如果只打印 warning 然后 exit 0，CI 和 Agent 都会漏掉。
    """
    problems: list[str] = []

    print("== 静态检查（AST，不执行模块） ==")
    static_keys, static_keywords, blockers = scan_static(MEMES_DIR)
    print(
        f"扫描 {len(iter_meme_dirs(MEMES_DIR))} 个目录，"
        f"解析出 {len(static_keys)} 个 meme key、{len(static_keywords)} 个 keyword"
    )

    dup_keys = find_duplicates(static_keys)
    if dup_keys:
        problems.append("meme key 重复")
        for value, srcs in sorted(dup_keys.items()):
            print(f"  [blocker] meme key {value!r} 重复：{', '.join(srcs)}")
        print("            -> 上游 add_meme 只保留先注册的那个，后者被静默丢弃")

    dup_kw = find_duplicates(static_keywords)
    if dup_kw:
        problems.append("keywords 重复")
        for value, srcs in sorted(dup_kw.items()):
            print(f"  [warn]    keyword {value!r} 重复：{', '.join(srcs)}")
        print("            -> 本包内 keywords 只是元数据，不会互相覆盖；")
        print("               但消费端适配器拿它当触发词，重复可能使其中一方不可达")

    if blockers:
        problems.append(f"静态扫描有 {len(blockers)} 处没完成")
        for b in blockers:
            print(f"  [blocker] {b}")

    if not dup_keys and not dup_kw and not blockers:
        print("  meme key 重复       : 无")
        print("  keywords 触发词重复  : 无")
        print("  静态扫描            : 无跳过项")

    print()
    print("== 动态注册（真实加载 memes/） ==")
    print(f"注册成功 {len(registered)} 个，memes/ 下目录 {len(expected_dirs)} 个")
    for k in registered:
        print(f"  {k}")

    # 逐一比对，而不是只比总数：
    # 「一个目录注册失败 + 另一个目录多注册一个」会让总数刚好相等，
    # 只比总数就把真正的失败掩盖掉了。
    static_set = {k for k, _ in static_keys}
    missing = sorted(static_set - set(registered))
    extra = sorted(set(registered) - static_set)

    if len(registered) != len(expected_dirs):
        problems.append("注册数与目录数不一致")
        # 双向说明：少了 = 有目录没注册成功；多了 = 有目录多注册（违反一目录一表情）
        if len(registered) < len(expected_dirs):
            hint = f"少了 {len(expected_dirs) - len(registered)} 个（有目录没注册成功）"
        else:
            hint = f"多了 {len(registered) - len(expected_dirs)} 个（有目录产生了额外注册）"
        print(
            f"  [blocker] 目录 {len(expected_dirs)} 个但注册了 {len(registered)} 个，{hint}。"
        )
    if missing:
        problems.append("有 key 没注册成功")
        print(f"  [blocker] 静态扫到了但没注册成功：{', '.join(missing)}")
        print("            最常见的是与上游内置表情撞 key（本仓库那个被丢弃），")
        print("            也可能是模块导入失败、或 key 在禁用列表。在上面日志里搜")
        print("            'already exists' / 'Failed to import' / 'disabled list'。")
    if extra:
        problems.append("有注册结果静态扫不到")
        print(f"  [blocker] 注册成功了但静态没扫到：{', '.join(extra)}")

    print()
    if problems:
        print(f"检查未通过：{'、'.join(problems)}")
        return 1
    print("检查通过")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="用 meme_generator 渲染本仓库的表情，并打印产物绝对路径",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-m", "--meme", default=DEFAULT_MEME, help=f"表情 key，默认 {DEFAULT_MEME}")
    parser.add_argument("-t", "--text", action="append", help="文字，可重复传入以填多个文本槽")
    parser.add_argument("-o", "--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="输出目录")
    parser.add_argument("-n", "--name", help="输出文件名，默认 <表情 key>.png")
    parser.add_argument("--open", action="store_true", help="渲染后用系统默认程序打开图片")
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出本仓库表情并做重复/注册自检（有问题退出码非 0）",
    )
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows 控制台默认不是 UTF-8

    keys, expected = load_repo_memes()

    if args.list:
        sys.exit(report_check(keys, expected))

    from meme_generator import get_meme, get_meme_keys
    from meme_generator.exception import MemeGeneratorException

    # 必须确认这个 key 真的由本仓库注册，不能拿到就渲染。
    #
    # 全局注册表 _memes 里挂着 meme_generator 自带的近 300 个内置表情。
    # 如果本仓库某个 key 恰好撞了内置表情，add_meme 会丢弃本仓库那个、
    # 保留内置版本；此时 get_meme() 依然能查到 —— 于是「实际渲染验证」
    # 验的其实是上游那个表情，本仓库这份代码从没被执行过。
    if args.meme not in keys:
        known = args.meme in set(get_meme_keys())
        reason = (
            "这个 key 在全局注册表里存在，但**不是本仓库注册的**。\n"
            "最可能是与 meme_generator 内置表情撞名，本仓库那个被丢弃了。\n"
            "（本工具只渲染本仓库的表情，要渲染内置表情请直接用上游 CLI。）"
            if known
            else "这个 key 在注册表里完全不存在。"
        )
        sys.exit(
            f"表情 {args.meme!r} 没有从本仓库成功注册。\n{reason}\n"
            "先跑 `python tools/render_meme.py --list` 看具体是哪种冲突。\n"
            "本仓库注册成功的 key：\n  " + "\n  ".join(keys)
        )

    try:
        meme = get_meme(args.meme)
    except Exception:  # noqa: BLE001   NoSuchMeme
        sys.exit(
            f"表情 {args.meme!r} 注册表里查不到（上面刚检查过它在本仓库 keys 里，"
            "属于异常情况）。本仓库注册成功的 key：\n  " + "\n  ".join(keys)
        )

    p = meme.params_type
    texts = args.text or list(p.default_texts)
    if len(texts) < p.min_texts:
        sys.exit(
            f"表情 {args.meme!r} 需要至少 {p.min_texts} 段文字"
            f"（可用 -t 传入，最多 {p.max_texts} 段），且它没有可用的默认文字。"
        )

    out_path = (args.out_dir / (args.name or f"{args.meme}.png")).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"表情      : {meme.key}")
    print(f"关键词    : {' / '.join(meme.keywords) or '（无）'}")
    print(f"文字约束  : {p.min_texts}..{p.max_texts} 段，图片 {p.min_images}..{p.max_images} 张")
    print(f"本次文字  : {texts}")

    try:
        # Meme.__call__ 是 keyword-only，且会自己校验文字/图片数量
        buf = meme(texts=texts)
    except MemeGeneratorException as e:
        sys.exit(f"生成失败（{type(e).__name__}）：{e}")

    if hasattr(buf, "seek"):
        buf.seek(0)
    data = buf.read() if hasattr(buf, "read") else bytes(buf)
    existed = out_path.exists()
    out_path.write_bytes(data)

    print()
    print(f"{'已覆盖' if existed else '已写入'}: {out_path}")
    print(f"大小      : {len(data) / 1024:.1f} KB")
    print(f"目录      : {out_path.parent}")

    if args.open:
        open_file(out_path)


if __name__ == "__main__":
    main()
