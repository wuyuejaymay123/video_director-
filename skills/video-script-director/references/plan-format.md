# 文案导演包格式 v1

所有输出以 `director-plan.json` 的内容为准。它是本 Skill 的中间格式，不宣称已有剪辑软件能直接导入。有执行工具时先按此格式写 JSON，再运行可选脚本 `scripts/director_package.py`；无执行工具时直接按此格式产出 JSON 与对应文档，不能把没有 Python 当作无法写稿的理由。用户已指定文件格式时，保留等价信息即可，不必强制改用 JSON。

## 文件与命令

```text
python <skill>/scripts/director_package.py <项目>/director-plan.json --check
python <skill>/scripts/director_package.py <项目>/director-plan.json --out <项目>/交付
```

`--out` 导出 `口播稿.md`、`拍摄导演表.md`、`剪辑交接单.md`、`素材清单.md`、`edit-brief.json`。已有同名文件默认不覆盖；明确更新当前版本时用 `--overwrite`，或者写入新版本目录。相对素材路径以输入 JSON 所在目录为基准；导出 JSON 中的本地文件路径转为绝对路径。跨设备移交时一并带上媒体目录，并在新设备将路径重设为实际可访问的位置；不要把某台电脑的绝对路径当通用地址。

纯聊天模式可用文件名作标题并输出可复制内容：口播全文、导演表、剪辑单、素材清单、完整 JSON。保留所有信息而不伪造下载链接；若回复长度不足，先交完整纯稿和导演时间线，再按自然段续交其余内容，不用省略号替代缺失台词。

校验检查结构、时序、文字锚点和资源引用，不证明事实、审美、音质或完播效果。保留校验警告并处理可解决的问题。

## 顶层字段

下列字段必需；允许增加说明字段，不要删除本合同的字段。

```json
{
  "schema_version": "1.0",
  "project": {
    "title": "具体标题",
    "topic": "用户原主题",
    "angle": "本期只解决的具体问题",
    "audience": "观众是谁以及正遇到什么问题",
    "platform": "抖音/小红书",
    "target_duration_s": 60,
    "aspect_ratio": "9:16",
    "mode": "rewrite",
    "assumptions": ["未提供实录，以下时码是排练预估"]
  },
  "timing": {
    "basis": "estimated",
    "rate_cps": 4.5,
    "source_media": null,
    "transcript_path": null,
    "note": "按语速、停顿和画面停留估算；剪辑前按录音重对齐"
  },
  "direction": {
    "promise": "看完能采取的具体行动",
    "emotion_arc": "先认出困境，随后好奇，看到例子后理解，最后愿意试一次",
    "persona": "像给一个朋友演示，避免播音腔",
    "visual_style": "按本片选择的画面风格",
    "audio_style": "自然人声优先",
    "cover_title": "封面文字",
    "revision_notes": ["合并了重复铺垫"]
  },
  "fragments": [],
  "claims": [],
  "assets": [],
  "segments": []
}
```

`project.mode`：`rewrite` 整稿优化、`topic` 主题成稿、`integrate` 片段融合。有长稿又有锁定句时用 `rewrite` 并填写 fragments。`target_duration_s` 是目标，实际规划总长是最后一段 `end_s`。超目标不要偷偷改快语速，先压缩重复内容，必要时说明取舍。

`timing.basis`：`estimated` 未拍摄的排练预估；`aligned` 已按真实音轨对齐。`aligned` 必须提供存在的 `source_media`、`transcript_path`，并说明对齐方式及核对范围；仅存在文件不证明对齐正确。`rate_cps` 是本片估算参数（不是平台规律），默认可从 4.5 起算，英文、数字和专业词按实际读法复核。

## 每段 segments[]

每段对应一个可单独排练的意群；长段可以拆分，不能用省略号代替完整台词。

```json
{
  "id": "S01",
  "start_s": 0,
  "end_s": 6,
  "speech": "你的稿子全是干货，为什么观众还是划走？",
  "purpose": "让正在遭遇此事的观众认出自己",
  "techniques": ["共鸣", "自问"],
  "performance": {
    "emotion": "困惑中带理解",
    "intensity": 2,
    "pace": "前半句正常，为什么略慢",
    "emphasis": ["全是干货", "还是划走"],
    "pauses": [{"after": "干货，", "seconds": 0.3}],
    "face": "看镜头，轻抬眉",
    "gesture": "手掌向上问一次，随后收回"
  },
  "camera": {
    "visibility": "露脸",
    "framing": "胸口以上中近景",
    "action": "固定机位，轻微前倾；无需真的推动相机"
  },
  "visual": {
    "description": "画面保持简洁，让观众先看人",
    "asset_ids": []
  },
  "edits": [{
    "id": "E01",
    "anchor": "还是划走",
    "occurrence": 1,
    "offset_s": 4.1,
    "duration_s": 0.6,
    "priority": "must",
    "intent": "让划走这个后果被看见",
    "visual": "字幕划走二字向上离开一次，随后恢复正常字幕",
    "sound": "不加冲击音",
    "voice": "保留自然人声，不做变声"
  }],
  "claim_ids": [],
  "fragment_ids": []
}
```

- `start_s/end_s`：全片时间，单位秒，从 0 连续递增、无重叠无缺口。静默画面单独成段，`speech` 可为空，但 `purpose/visual.description` 说明停留用途。拍摄表显示完整台词、露脸状态和全部表演细节。
- `intensity`：1–5，只描述相对情绪强度；不能整条都是 5。
- `pauses.after`、`emphasis`、`edits.anchor` 必须在本段 speech 中逐字可找到。停顿包含在段时长内；无台词段使用空 anchor、occurrence=1，以段落起点触发。
- `offset_s`：本段起点到效果开始的秒数；全片时间= start_s + offset_s。estimated 时同样是预估，剪辑师必须重新对到实录关键词。
- `occurrence`：anchor 在本段出现多次时取第几次，1 起算。优先用足够独特的短语，不用歧义单字。问句的否定表达也可能包含答案的子串，应用包含后续词的完整片段避免误定位。`pauses` 也可附 occurrence；同一停顿短语重复时明确指定，否则按第 1 次处理。
- `duration_s`：效果从开始到结束的时长，包括阅读停留；单段效果不跨段。跨段效果拆成两项并在描述中说明承接。
- `priority`：`must` 承载理解/反转的重点剪辑；`optional` 可按预算省略。`visual/sound/voice` 可明确写“无/保留原声”。
- 重音不等于爆音；具体写出现什么、如何变化、停多久、何时恢复。全片只把有语义价值的节点设为 must。
- 可选 `read_units`：按实际读法折算的读音单位，供数字、英文多的段落估时。没有时，程序只以去掉标点后的字符数作粗略警告。

## 保留句 fragments[]

```json
{"id":"F01","text":"别让观众替你翻译。","policy":"verbatim","segment_ids":["S06"],"reason":"作为方法总结"}
```

`policy`：`verbatim` 原句逐字保留（含标点）、`meaning` 保留意思允许润色。已采用的片段必须引用存在的段落，并与这些段落的 `fragment_ids` 双向对应。原句如需跨段，应先按用户允许的边界拆成独立片段；不得利用跨段拼接偷偷修改句子。verbatim 必须完整出现在至少一个所引用段落中。

可选 `disposition` 默认为 `included`（已采用）。锁定片段存在未解决的事实/逻辑冲突、无法原样安全纳入时，用 `reserved`（保留待处理），`segment_ids` 必须为空，`reason` 写清冲突和建议替换，不被任何段落引用。此时不用强行将原句塞入口播以通过校验。交付要醒目标记“待处理，未纳入口播”，不能声称用户的保留要求已全部满足；继续完成不受影响的文案。不可因单纯难改而滥用 reserved。

## 事实 claims[]

```json
{"id":"C01","text":"需要核实的具体说法","status":"needs_verification","source":"","note":"暂不作确定性口播，改为待验证问题"}
```

status：`verified` 当前核实且给来源、`user_provided` 用户提供但未独立核实、`hypothetical` 明确假设/原创场景、`needs_verification` 未解决。程序只检查字段和引用；由写稿者核查实际措辞是否恰当。不要把有来源等同于有证据，或把用户提供等同于实测。

## 素材 assets[]

```json
{
  "id": "A01",
  "kind": "generated_image",
  "status": "planned",
  "purpose": "把抽象的信息过载变成可见场景",
  "path": null,
  "source": "原创概念示意，非真实界面或实验结果",
  "prompt": "主体、动作、构图、风格、比例、留白、避免元素齐全的生图指令",
  "negative": "不生成产品界面、不嵌入小字",
  "aspect_ratio": "9:16",
  "placement": "主体居中，上下留足字幕与平台控件空间",
  "fallback": "用真人手持纸张演示同一关系",
  "alt": "供无法看图时理解的简要描述"
}
```

`kind`：`generated_image`、`real_image`、`screen_recording`、`video`、`diagram`、`audio`。
`status`：`planned` 仅方案、`generated` 已实际生成且保存、`available` 已有可用文件、`needs_user_media` 待补录/补图、`failed` 获取失败。
`generated/available` 在本地文件交接模式下需要非空且存在的本地 path。纯聊天平台已返回原生图片/附件但没有本地路径时，展示原生结果，在素材清单说明“已生成，待导出到剪辑设备”，JSON 状态暂记 planned 并添加 `delivery_state: "native_output_only"`、`native_reference`（实际附件标识/链接），不可编造本地路径；告知状态字段描述的是可供本地剪辑取用的程度。下载/导出后再更新为 generated。`source` 写清来源/真实性；真实媒体填写来源 URL 或用户文件依据。`prompt` 对真实录屏改为具体拍摄清单，不用生图替代真实证据。

## 交给剪辑 Skill

把本次的 `口播稿.md`、`拍摄导演表.md`、`剪辑交接单.md`、`edit-brief.json`、媒体文件和实录一并交接。下一位执行者先读交接单，提取声音时间线，对齐 segment 的完整台词，再定位 edits.anchor 的第 occurrence 次出现，重算 offset 与持续时长；保留停顿/呼吸的表达意图，不机械照抄预估时码。

已有 `creator-video-studio` 或 `talking-head-edit` 时，读取其当前 SKILL.md 再适配，不能仅凭名称断言字段兼容。`edit-brief.json` 是给 agent 读取的合同，不是 Remotion、剪映或 HyperFrames 的原生工程。未实际适配和渲染，只能报告“已产出可供读取的剪辑要求”。
