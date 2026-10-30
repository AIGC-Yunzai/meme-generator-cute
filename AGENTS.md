# AGENTS.md

`meme-generator-cute` 是表情包生成器 [MeetWq/meme-generator](https://github.com/MeetWq/meme-generator) 的第三方表情仓库。
本仓库只存放表情素材（`.png`）与表情实现（`memes/<name>/__init__.py`），运行时由上游加载。

## 未获允许不得提交或推送

**没有仓库维护者的明确允许，不得执行 `git commit`、`git push`，也不得用任何等效手段（`gh pr create`、`gh api` 改远端、rebase/push 组合等）把改动落到远端或历史里。**

- 「明确允许」= 维护者在**当次对话**里针对**本次改动**点了头。之前某次允许过，不代表这次也可以。
- 改完文件就停在「工作区有改动」这一步，把 `git status` / `git diff` 的结果报给维护者，等指示。
- 允许只覆盖被批准的范围：批准了 commit 不等于批准 push；批准了某个分支不等于批准 `main`。
- 需要提交信息时，先把拟用的 commit message 写出来给维护者看，别直接 `git commit` 完再汇报。
- 反向也要说清：**「落地」「提交」都只算 commit，不包含 push。** push 必须明说「push」或「推到远端」，
  别把「落地」读成上线。

## 目录结构

```
memes/<meme_name>/
  __init__.py             # 实现 + add_meme 注册
  images/                 # 素材；一般只有一张主图，多图按 01.png、02.png … 命名
docs/
  meme_keywords.py        # 扫描 memes/ 生成 docs/meme_keywords.md，再同步到 Wiki
  agents/                 # 工程技能的仓库级配置（issue tracker / triage 标签 / domain 布局）
tools/
  measure_bubble.py       # 命令行测量气泡内可用文字范围
  render_meme.py          # 本地渲染预览 + 重复自检，产物落到 tools/out/（已 gitignore）
.github/workflows/        # Wiki 文档自动更新，无需手工干预
```

`docs/meme_keywords.md` 是脚本产物，只由 CI 推到 Wiki，不进仓库（已写进 `.gitignore`）。

## 常用命令

| 用途 | 命令 |
| --- | --- |
| 安装依赖 | `pip install -U "meme_generator<0.2.0" filetype pillow` |
| 生成关键字文档 | `python docs/meme_keywords.py` |
| 测量气泡文字范围 | `python tools/measure_bubble.py memes/<name>/images/<img>.png [--seed x,y]` |
| 本地渲染预览 | `python tools/render_meme.py -m <key> -t "文字"`（`--open` 可直接看图） |
| 带表情参数渲染 | `python tools/render_meme.py -m <key> --args '{"number": 2}'` |
| 多张预览拼一张 | `python tools/preview_sheet.py tools/out/a.png tools/out/b.png -o tools/out/sheet.png` |
| 冲突自检 + 列表情 | `python tools/render_meme.py --list`（有问题退出码非 0） |
| 语法检查 | `python -m py_compile memes/<name>/__init__.py` |

仓库内没有测试框架。**最低限度验证**是这四条，少一条就还差一层：

1. `python -m py_compile memes/<name>/__init__.py` —— 只证明语法成立
2. `python docs/meme_keywords.py` —— 只证明 AST 抽取能跑通
3. `python tools/render_meme.py --list` —— 查重复 + 真实加载 `memes/`，有问题非 0 退出
4. 对本次改动的表情**实际渲染一次**：`python tools/render_meme.py -m <key> -t "测试文字"`

第 1、2 条**都不执行表情模块**，所以 `add_meme` 参数类型错误、依赖 import 失败、
`draw_text` 区域写错之类都能躲过去；只有第 3、4 条会真正走到 `add_meme` 与 `draw_text`。

### 两类「重复」不是一回事

`docs/meme_keywords.py` 只做 AST 抽取，**不检测任何冲突**。而冲突有两种，性质完全不同：

| | meme key | keywords（触发词） |
| --- | --- | --- |
| 是什么 | 上游注册表 `manager._memes` 的键 | `Meme` 的元数据，`cli.py` 只拿它当 `help_text` |
| 重复的后果 | `add_meme` 只 warning 后 `return`，**保留先注册的、丢弃后注册的** | 本包内**不会**互相覆盖；消费端适配器拿它当触发词，重复可能使其中一方不可达 |
| 怎么查 | `tools/render_meme.py --list`（两类一起查） | 同上 |

`--list` 分两段：**静态**用 AST 扫 `memes/*/__init__.py`，查仓库内重复的 key 与 keyword；
**动态**真实 `load_memes(memes/)` 再对比「注册成功数 vs 目录数」——
只有这一步能发现**本仓库与上游内置表情的 key 冲突**，静态扫描看不到内置表。

「注册数 ≠ 目录数」只说明**至少有目录没成功注册**，原因还可能是模块 import 失败、
key 在禁用列表等，不必然是 key 冲突；要去日志里搜 `already exists` /
`Failed to import` / `disabled list` 确认。

## 本地渲染预览

**建议装到独立 venv**，别污染系统 Python 里已有的 pillow/pil-utils：

```bash
python -m venv <venv>
<venv>/Scripts/python.exe -m pip install "meme_generator<0.2.0" filetype pillow
<venv>/Scripts/python.exe tools/render_meme.py -m deep_seek_think
```

产物默认落在 `tools/out/<表情 key>.png`，脚本会打印**绝对路径**；加 `--open` 直接调系统看图器。

**表情自己的参数走 `--args`（JSON 对象），不要指望命令行短选项。** 工具自己的 `-n` 是**输出文件名**，
和表情的 `-n`（图片编号）不是一回事：表情的短选项在这里传不进去，只能写进 `--args`。

```bash
# 指定用第 2 张素材，输出叫 preview.png
python tools/render_meme.py -m honest_money --args '{"number": 2}' -n preview.png
```

这条是硬约束：上游 `add_meme` 不按 type hint 做运行时校验，`--args` 里写错键名或类型
要到真正调用表情时才炸；没有 `--args` 时，「指定编号」这条路径根本跑不到。

**要对比多个版本（字号、描边、换素材）时，先拼一张再读图**：`tools/preview_sheet.py` 把多张
竖着拼起来并标序号。字号差 4px、描边差 1px，单看一张根本看不出来，并排才看得出来；
顺带把读图成本从 N 次降到 1 次。

三个容易踩的点：

- **字体**：需要系统里能解析到中文字体（Windows 的微软雅黑即可）。
  上游 `resources/fonts/` 是可选的；找不到字体时 `draw_text` 会报错。
- **`SkIcuLoader: datafile missing ... icudtl.dat`**：Windows 上 skia 的已知告警，**非致命**
  （中文照常渲染），不用去补那个文件。
- **Linux / 容器 / CI 上 `import meme_generator` 报 `libEGL.so.1: cannot open shared object file`**：
  skia 要系统级的 EGL/GL 库，`apt install libegl1 libgl1` 就好。这条在本地 Windows 永远
  复现不了，只有换到 Linux 才炸——写 Dockerfile 或新 workflow 时先装它。

写脚本落盘时注意：`BuildImage.save()` **不是** PIL 的 `Image.save(path)`，
它的签名是 `save(format: str) -> BytesIO`——第一个参数是格式名，而且只返回内存对象、不写文件。
落盘要么 `frame.save_png()` 拿 bytes 再 `write_bytes`，要么 `frame.image.save(path)` 走 PIL。

`render_meme.py` 是用 `meme_generator.load_memes(memes/)` 走**上游真实注册路径**的，
所以 `--list` 能验证：模块可导入、`add_meme` 的注册过程能跑完、注册结果与目录对得上。
但它**不能**证明 `add_meme` 的参数合法 —— 上游 `add_meme()` 只是把参数塞进
`MemeParamsType` / `Meme` 两个 dataclass，不会按 type hint 做运行时校验，
有些错值照样能注册成功，直到真正调用 `Meme.__call__()` 才暴露。
参数与绘图路径只能靠**实际 render** 验证，这是 `docs/meme_keywords.py` 完全做不到的。

另外 `-m <key>` 只接受**本仓库注册成功的 key**：全局注册表里挂着上游近 300 个内置表情，
如果本仓库某个 key 撞了它们，本仓库那个会被丢弃而 `get_meme()` 依然查得到 ——
那样「渲染验证」验的就是上游那个表情，本仓库代码从没被执行过。所以这一步是硬拦截。

## 新增一个表情

1. 建目录 `memes/<meme_name>/`，放素材到 `images/`。
2. 复制一个语义相近的既有实现作为起点（如 `memes/lastOrderThink/`）。
3. 定文字范围：素材**有气泡**就用 `tools/measure_bubble.py` 量；**没有气泡**的（影视截图、
   要模仿原片自带字幕）就不要用量气泡的工具，字幕区怎么定见 `docs/adr/0001`。
4. 注册 `add_meme`，跑 `python docs/meme_keywords.py` 自检。
5. 渲染确认：`python tools/render_meme.py -m <key> --open`，
   看文字有没有出气泡、有没有折成「孤字行」（末行只剩一个字）。
6. Wiki 文档由 CI 自动更新，不要手工改 `docs/meme_keywords.md`。

## 约定

- 目录名沿用仓库既有的 lowerCamelCase（`lastOrderThink`）或 snake_case（`anan_say`）均可，
  但 `add_meme` 的第一个参数（meme key）**统一用小写下划线**，
  并尽量与目录名的词序一致：`lastOrderThink/` → `last_order_think`，`deepSeekThink/` → `deep_seek_think`。
- 每个表情必须有 `min_texts` / `max_texts` / `default_texts` / `keywords` / `tags` / `date_created` / `date_modified`。
- **一个目录恰好注册一个表情**（`add_meme` 只能出现一次）。`docs/meme_keywords.py` 只取第一处调用，
  `render_meme.py --list` 也会把「不是 1 处」判成 blocker。
- **`add_meme` 的 key 和 `keywords` 必须写成脚本能静态解析的字面量**：key 是字符串字面量，
  `keywords` 是列表字面量且元素都是字符串。写成 `KEYWORDS = [...]` 再 `keywords=KEYWORDS`
  会让重复检测**静默失效**，所以 `--list` 把这种「扫描跳过关键字段」直接算 blocker，不是 warning。
- 文字画不下时抛 `TextOverLength(text)`，不要静默截断：
  ```python
  try:
      frame.draw_text(...)
  except ValueError:
      raise TextOverLength(text)
  ```
- `fill` 取素材气泡描边的同色系深色，让文字像气泡自带的字（`lastOrderThink` 用 `#5a3a1c`）。
  字幕类表情是例外：固定纯白字 + 纯黑描边，见 `docs/adr/0001`。
- **带参数的表情**（多图选择、开关）照 `memes/elysia_holdsign/` 抄：参数模型用上游的
  `MemeArgsModel` / `MemeArgsType` / `ParserOption`（定义在 `meme_generator/meme.py`），
  本地用 `render_meme.py --args` 传。参数约定见 `docs/adr/0002`。

## 气泡文字范围怎么定

`draw_text` 的矩形只要「大致」落在气泡内即可，不要手写超大范围，否则文字会溢出气泡。
`tools/measure_bubble.py` 用洪水填充圈出气泡内部
（描边 1px 膨胀 → 洪水填充 → 排除底部细尾巴 → 按比例内缩），输出外接框、主体底边与建议范围：

```bash
python tools/measure_bubble.py memes/deepSeekThink/images/DSniangThink.png --seed 450,250
```

它已按 `lastOrderThink` 的既有手工值校准：对 `lastOrderThink.png` 输出 `(130, 105, 745, 505)`，
与该表情实际使用的 `(120, 110, 740, 500)` 相差不到 10px（图宽 1681）。
气泡底部那条细尾巴会被自动排除，不参与计算。

**建议范围是起点，不是标准答案。** 内缩比例是照 `lastOrderThink` 这一个表情校准出来的统一经验值，
不按气泡形状自适应，所以对**椭圆气泡**（如 `DSniangThink`）会偏保守：
`body_bottom` 那条「宽度 ≥ 最宽处 50%」的判定会把椭圆下半部分当成尾巴切掉，
算出的矩形**四角其实落在气泡外**。文字是居中的，实际不越界（实测默认文字墨迹
x 179..719 / y 213..320，远在气泡外接框 (94, 32, 813, 492) 之内），
但要精确卡边就得手改 `TEXT_AREA` 再渲染出来看。

改完文字范围**务必用 `tools/render_meme.py` 渲染一次** —— 这个矩形能不能画下、
画出来好不好看，只有真渲染一次才知道，量出来的数字本身说明不了。

### 定位已经画上去的字：与原素材差分

想知道成品里字到底落在哪，**拿成品和原素材做差分**：`abs(a - b).sum(2) > 6` 的 bbox
就是这次画上去的全部像素（含描边），精确到像素。比按亮度阈值找白字可靠得多——
画面里的白色高光、浅色衣领会一起算进去（实测把 635..1036 量成 526..1230，中心偏 40px）。

这个技巧**只用于测量**；拿整图 diff 当回归断言会假红，原因见「注意事项」最后一条。

`measure_bubble.py` 会拒绝越界 seed，并在填充区域**触及图片四边**时报错：
那说明种子点不在封闭气泡内（点在透明背景上，或描边有缺口导致漏填充），
此时算出来的外接框是垃圾。报错比输出一个「看起来还挺像回事」的巨大建议范围安全得多。

两个实测基准（改了内缩比例后可用它们回归）：

| 素材 | 尺寸 | 气泡外接框 | 主体底边 | 建议范围 | 实际使用 |
| --- | --- | --- | --- | --- | --- |
| `lastOrderThink.png` | 1681×1681 | (36, 40, 838, 616) | 532 | (130, 105, 745, 505) | (120, 110, 740, 500) |
| `DSniangThink.png` | 1026×1026 | (94, 32, 813, 492) | 442 | (175, 85, 730, 420) | (175, 85, 730, 420) |

注意 `draw_text` 的参数名是 `font_size`，且 `max_fontsize` / `min_fontsize` **只在传矩形区域时生效**；
`halign` / `valign` / `lines_align` 的默认值分别是 `center` / `center` / `left`（本仓库统一显式写 `lines_align="center"`）。
文字放不下时从 `max_fontsize` 每次 −1 试到 `min_fontsize`，仍放不下才抛 `ValueError`。

## 注意事项

- **目标 Python 版本是 3.9**（见 `pyproject.toml`），CI 用 3.10。不要用 3.10+ 才有的语法。
- **`docs/meme_keywords.py` 只静态解析 AST，不执行表情模块**，而且**并非支持所有静态表达式** ——
  它只认脚本里明确写了处理逻辑的那几种形态。所以 `default_texts=[DEFAULT_TEXT]`（既有表情都是这样）
  取不到值，生成的表格里「默认文字」一列为空；`date_created=datetime(...)` 这种调用是**特判**支持的，
  严格说并不是「字面量」。保持一致即可；若想让文档显示默认文字，得在注册处直接写字符串字面量。
  要更进一步（解析模块级常量）得改 `docs/meme_keywords.py`，但那份文件是 CI 在用的，改前先想清楚。
- 两个 Wiki workflow 都监听 `main`：`generate_keywords.yml` 写 `emoji_list.md`，
  `update_emoji_list.yml` 写 `wiki_emoji_list.md`。**仓库没有 `master` 分支**，
  workflow 的 `branches` 里写成 `master` 就永远不会触发——`generate_keywords.yml` 曾这样
  静默死了五个月，关键词 Wiki 一直停在旧数据。
- 素材来自网络，新增图片请确认可收录，仓库声明见 `README.md`。
- **不要用「整图逐像素 diff」给表情写回归测试**：`DSniangThink.png` 的透明背景像素里
  存的是白色 RGB（如 `(255,254,255,0)`），PIL 保存 PNG 时会把 alpha=0 的 RGB 归零，
  于是输出与原图的 diff 会覆盖整张图；再叠上素材自带的抗锯齿边缘，噪声更大。
  要断言文字位置，应只在原图 `alpha == 255` 的像素上求墨迹 bbox。
- **做「拟态 UI」的表情**（例如在用户文字上方补一行 DeepSeek 那样的状态行，
  参考 `memes/deepSeekThink/`）有五个固定坑：
  1. **水平定位要用 `TEXT_AREA` 的中心，别用 `frame.width / 2`。**
     素材是 1026 宽而气泡只有 94..813，按整图居中会让内容整体右偏约 60px。
  2. **状态行与正文要左对齐**（模仿真 UI 的排版）。`deepSeekThink` 的做法是：先把两者
     各画到一张透明层，用 `img.image.getchannel("A").getbbox()` 量出**真实墨迹 bbox**，
     再让两张层的墨迹左边缘落在同一个 x 上，整组按较宽的那个在气泡里居中。
     好处是对齐是像素级的，而且**不用复制 pil_utils 那套「从 max_fontsize 往下试」的
     字号拟合逻辑**去估算文字宽度 —— 那套逻辑一旦和上游不同步，对齐就会悄悄偏掉。
  3. **需要单行时把 `allow_wrap` 设成 `False`。**
     否则 `draw_text` 会优先「折成两行用大字号」，排出「八个字也不多 / 啊」
     这种末行孤字，还会顶到上面的状态行。不折行它就会自己缩字号保住单行。
  4. **图标、折角这类小元素用 `draw_ellipse` / `draw_line` 画，别用字体里的 `⚛` `›`。**
     那些字符依赖 Segoe UI Symbol 之类的字体，换台 Linux 机器可能变豆腐块。
     PIL 的图形没有抗锯齿，放大 4 倍画完再 `resize` 缩回来即可（见 `_SUPERSAMPLE`）。
  5. **要补状态行就得排除含换行的输入。** `allow_wrap=False` 只挡自动折行，挡不住用户自己写的 `\n`；
     多行正文会被压进小区域再纵向居中，行数一多首行就顶到状态行上
     （实测「上\n下」的正文首行在 y=189，状态行底边 187，只差 2px）。
     `deepSeekThink` 的判据是「字数 ≤ `SHORT_TEXT_MAX` **且**不含 `\n` / `\r`」。

## Agent skills

### Issue tracker

Issue 与 spec 记为 GitHub Issue，用 `gh` CLI 读写 `AIGC-Yunzai/meme-generator-cute`；外部 PR 不算请求入口。详见 `docs/agents/issue-tracker.md`。

### Triage labels

triage 五个状态角色沿用默认标签名（`needs-triage` / `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix`），类别沿用既有的 `bug` / `enhancement`。详见 `docs/agents/triage-labels.md`。

### Domain docs

单上下文（single-context）：一个 `GLOSSARY.md` + 一个 `docs/adr/`，都已建，动手前先读。这两处的具体约定只写在 `docs/agents/domain.md`，这里不再复述一份（复述过的都过期了）。

## 参考

- 上游加载第三方表情的方式：<https://github.com/MemeCrafters/meme-generator/wiki/加载其他表情>
- `AGENTS.md` 格式说明：<https://agents.md/>
