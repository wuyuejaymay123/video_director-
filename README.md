# 短视频文案与镜头导演

把一个主题、一篇稿子，或几句你想保留的话，整理成 **能照着说、照着拍、交给剪辑继续做** 的短视频方案。

Skill 名称：`video-script-director`。采用通用 Markdown 指令和 JSON 格式，支持原生 Skill 加载，也提供普通聊天助手可直接使用的完整提示词。

## 下载与使用

- **Codex、Claude、WorkBuddy 等 Agent：** [下载独立 Skill ZIP](https://github.com/wuyuejaymay123/video_director-/raw/refs/heads/main/dist/video-script-director-universal-v1.0.zip)，按 [各平台安装与调用指南](docs/agents.md) 操作。
- **豆包、DeepSeek 等聊天助手：** 打开 [通用提示词](skills/video-script-director/通用提示词.md)，复制全文到新对话，再发送你的主题或文案。
- **先看看效果：** [60 秒主题示例](examples/topic/口播稿.md) · [拍摄导演表](examples/topic/拍摄导演表.md) · [剪辑交接单](examples/topic/剪辑交接单.md)。

上传技能时使用上面的独立 ZIP。GitHub 的 **Code → Download ZIP** 下载的是整个仓库，不能直接当成单个技能包上传。

## 能做什么

| 你提供的内容 | Skill 的工作 |
| --- | --- |
| 完整文案 | 保留主题和个人语气，调整开头、顺序、例子、冗余和口语表达 |
| 只有主题 | 收窄切口，写完整口播，设计共鸣、自问自答和具体场景 |
| 喜欢的句子/段落 | 融入整篇结构，补齐前后衔接；标明“一字不改”的句子按锁定处理 |
| 拍摄与剪辑需求 | 给逐段情绪、重音、停顿、表情、动作、镜头及词语触发的动效/声音要求 |

四个核心方法：用体验说明抽象概念；回应观众此刻的疑问；控制每段信息量；让语速、情绪和信息顺序有变化。按内容需要使用，不机械堆砌口头禅或夸张表演。

## 直接复制这段开始

```text
用 video-script-director 帮我做一条短视频。
主题：为什么我一开摄像头就像在念稿。
观众：刚开始拍口播的人。
平台：抖音，目标时长 60 秒，语气像朋友聊天。
请给我完整口播、逐段时间线、情绪/重音/停顿/动作、
镜头安排和剪辑交接。哪里共鸣、举例、自问自答要具体标明。
这次不生成图片，只给需要的画面方案。
没有真实录音时，时间线标为排练预估。
```

更多：[三种输入与剪辑交接指令](docs/prompts.md)。

## 交付内容

- `director-plan.json`：整套方案的结构化主文件。
- `口播稿.md`：可直接放进提词器。
- `拍摄导演表.md`：每段预计秒数、台词、表演和镜头。
- `剪辑交接单.md`：重点词语、出现次数、动效、字幕、音效和人声处理。
- `素材清单.md`：素材用途、来源、状态和缺失时的替代方案。
- `edit-brief.json`：交给下游剪辑 Agent 改编使用的数据。

需要配图且宿主有图像工具时可实际生成；只有文本能力时交付画面方案和提示词。JSON 是跨 Agent 交接格式，不是剪映、Premiere 等软件的直接导入工程。拍摄前的时码是估算，拍完要依据实录重新对齐。

## 本地校验与导出（可选）

Python 3.10+，只用标准库。终端进入仓库根目录后执行：

```sh
python skills/video-script-director/scripts/director_package.py skills/video-script-director/examples/topic/director-plan.json --check
python skills/video-script-director/scripts/director_package.py skills/video-script-director/examples/topic/director-plan.json --out output/topic
python -I -X utf8 tests/test_director_package.py
python build_release.py
```

命令名是 `python3` 的环境相应替换；含空格的路径加引号。导出默认不覆盖已有文件，更新输出时显式添加 `--overwrite`。构建命令会更新通用提示词和 `dist/` 下载包。

不会运行 Python 也可以使用：让 Agent 按模板直接生成同样的内容即可。

## 兼容性与验证范围

核心格式参考 [Agent Skills 规范](https://agentskills.io/specification)。原生安装方式与普通聊天提示词方式见 [平台指南](docs/agents.md)，其中附有官方资料链接。

本次已在 Windows/Codex 环境完成本地安装与示例导出，17 项脚本测试通过。其他客户端的接入说明依据官方资料或通用文本输入方式整理，未逐个实机验收；不同宿主的文件、生图、联网和代码执行能力有差异。

脚本检查结构、时序和引用，不能证明事实正确、实录对齐或成片效果。Skill 不承诺播放量、涨粉或收益。

## 仓库结构

```text
skills/video-script-director/  核心技能、方法、格式、脚本、完整通用提示词
docs/agents.md                各 Agent 安装与调用
docs/prompts.md               三种输入与剪辑交接示例
examples/topic/               可直接查看的导出示例
tests/                        脚本回归测试
dist/                         独立 Skill ZIP 与校验清单
build_release.py              从源文件生成提示词和下载包
```
