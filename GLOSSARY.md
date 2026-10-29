# meme-generator-cute

第三方表情仓库：只存放素材（`images/*.png`）与表情实现（`memes/<name>/__init__.py`），
运行时由上游 `meme_generator` 加载注册。表情的语义边界（气泡表情 / 字幕表情 / 拟态 UI）
是这个仓库唯一真正需要精确用词的地方。

## 语言

**meme key**：
`add_meme` 的第一个参数，也是上游注册表 `manager._memes` 的键，统一小写下划线。
它与目录名不一定相同：`deepSeekThink/` 的 key 是 `deep_seek_think`。
_避免_：表情名、目录名

**keywords**：
表情的触发词，属于 `Meme` 元数据，下游适配器拿它匹配用户指令。
与 `tags` 无关——`tags` 只是分类标签，不参与触发。
_避免_：tags、触发标签、关键词标签

**TEXT_AREA**：
素材里带对话气泡的表情所使用的 `draw_text` 矩形，文字必须落在气泡内部。
_避免_：文字区、文本框、文字范围

**字幕区**：
素材是影视截图、画面里没有气泡的表情所使用的 `draw_text` 矩形。
文字模仿画面本身自带的那行字幕：水平居中、靠近画面底部、白字黑描边。
它不是 `TEXT_AREA`——字幕区不依附任何气泡，边界由原片的字幕行决定。
_避免_：字幕框、底部文字区

**blocker**：
`tools/render_meme.py --list` 以非零码退出的情形，与 warning 相对。
_避免_：错误、失败、报错
