# 各种 Agent 怎么使用

核对日期：2026-10-24。先选接入方式：**有 Skill 功能就加载完整技能目录；普通聊天就使用通用提示词全文。** 模型名称本身不决定工具能力。

| 环境 | 推荐入口 |
| --- | --- |
| Codex | 让 skill-installer 从本仓库安装，或放入其支持的技能目录 |
| Claude Code | 复制到个人或项目 `.claude/skills/` 目录 |
| Claude 网页/桌面端 | 在可用的自定义 Skills 界面上传独立 ZIP |
| WorkBuddy | 技能板块 → 添加技能 → 上传技能 |
| 豆包 | 在对话中粘贴完整通用提示词，再给任务 |
| DeepSeek | 在对话中粘贴完整通用提示词，再给任务 |
| 其他 Agent | 支持 Agent Skills 则加载目录，否则使用文本入口 |

## 1. Codex

**推荐：把下面这句话发给 Codex。**

```text
请使用 skill-installer 安装这个 GitHub 仓库中的技能：
仓库：https://github.com/wuyuejaymay123/video_director-
技能目录：skills/video-script-director
安装后确认它能被发现，并告诉我如何调用。
```

需要手动安装时，下载并解压 [独立技能包](../dist/video-script-director-universal-v1.0.zip)，将里面的 `video-script-director` 整个文件夹放到以下位置之一：

| 范围 | Windows | macOS / Linux |
| --- | --- | --- |
| 当前用户 | `%USERPROFILE%\.agents\skills\video-script-director\` | `~/.agents/skills/video-script-director/` |
| 当前项目 | `<项目>\.agents\skills\video-script-director\` | `<项目>/.agents/skills/video-script-director/` |

最终应是 `.../video-script-director/SKILL.md`，不要多套一层同名目录。上表依据当前 [OpenAI 官方技能文档](https://learn.chatgpt.com/docs/build-skills)。部分版本的内置安装器仍使用 `$CODEX_HOME/skills`（默认 `~/.codex/skills`）；使用安装器时以它报告的实际路径和发现结果为准，避免重复安装同名技能。

安装后在新一轮对话中输入：

```text
用 $video-script-director 优化下面的口播稿，目标 90 秒。
保留我的个人语气，给纯口播、拍摄导演表和剪辑交接。
这次只出方案，不生成图片。文案：……
```

支持技能选择器的客户端可选中该 Skill；自然语言说“使用短视频文案与镜头导演”也可以。未发现时先确认目录和 `SKILL.md`，再重新打开会话或重启客户端。

**不安装也能试用：** 在仓库目录中让 Codex “读取 `skills/video-script-director/SKILL.md` 和它引用的方法/格式，按它完成以下任务”。这是本次任务读取，不等于已全局安装。

## 2. Claude Code

下载独立 ZIP，解压后复制整个 `video-script-director` 文件夹：

- 个人使用：`~/.claude/skills/video-script-director/`。
- 项目使用：`<项目>/.claude/skills/video-script-director/`。
- Windows 的 `~` 指你的用户目录，通常为 `%USERPROFILE%`。

在 Claude Code 内调用：

```text
/video-script-director
主题：知识讲得越多，观众为什么反而越听不懂。
目标 60 秒，观众是知识博主。写完整口播，安排一组前后对比，
给逐段表演、时间线和剪辑要求。先不生成图片。
```

也可以在任务中直接点名技能。确认 Claude 能读到方法文件与格式文件；不要只复制 `SKILL.md` 而丢掉 `references/`。

依据：[Claude Code 官方 Skills 文档](https://code.claude.com/docs/en/skills)。这些本地目录属于 Claude Code；Claude 网页和 Cowork 不会因此自动读取电脑上的技能文件。

## 3. Claude 网页 / 桌面端

1. 下载 [独立 Skill ZIP](../dist/video-script-director-universal-v1.0.zip)，不需要解压后逐个上传。
2. 在支持该功能的账户中打开 **Customize → Skills**，通过上传入口导入 ZIP，并启用技能。
3. 如界面要求，先在设置中启用代码执行和文件创建能力；组织账户还受管理员策略影响。
4. 新建对话，点名“短视频文案与镜头导演”，然后发送主题、全文或想保留的片段。

上传包内的最外层是 `video-script-director/`，其内直接包含 `SKILL.md`。找不到上传入口时，改用下方通用文本方式即可。

依据：[Claude 官方使用说明](https://support.claude.com/en/articles/12512180-use-skills-in-claude)。按钮名称和可用性以当前客户端为准。

## 4. WorkBuddy

1. 下载本仓库的独立 Skill ZIP。
2. 打开左侧 **专家·技能·连接器**，选择 **技能** 页签。
3. 点击 **添加技能 → 上传技能**，选择 ZIP。
4. 在已安装列表确认技能存在且已开启，然后新建任务：

```text
使用已安装的 video-script-director，围绕“开口像念稿怎么办”
写一条 60 秒视频方案。给完整口播、拍摄导演表、素材清单和剪辑交接。
请把文件保存到本任务可写目录。这次不生成图片。
```

依据：[WorkBuddy 官方技能指南](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)。自行上传的包走上传入口；市场搜索不保证能搜到这个 GitHub 仓库。若当前版本没有入口，用完整通用提示词执行任务。

## 5. 豆包

使用普通聊天界面时：

1. 打开 [通用提示词.md](../skills/video-script-director/通用提示词.md)，复制文件正文全文。
2. 新建对话，粘贴全文。也可上传 Markdown 文件，但先确认助手能读到正文；只发文件名或仓库链接不能保证读取成功。
3. 紧接着发送你的任务：

```text
请按刚才的短视频文案与镜头导演方法处理：
主题：……；观众：……；平台：……；目标时长：90 秒。
给完整口播、逐段表演与镜头、剪辑重点。这次只出方案，不作图。
如果不能保存文件，就按文件名分块输出完整内容。
```

若提示词过长无法一次发送，按“核心流程 / 表达方法 / 输出格式”拆为三条，先声明“等我说发送完成再开始”，全部发完后给任务。换新对话需重新提供指引。

这里使用的是文本指引，不宣称豆包普通聊天界面具有原生 Skill 安装功能。能否生图、读附件或下载文件，以当前会话实际提供的功能为准。

## 6. DeepSeek

普通聊天界面的用法与豆包相同：**完整通用提示词 → 任务内容 → 接收方案**。

```text
按我提供的通用提示词优化下面的完整稿子。
主题不变，目标 90 秒，“别让观众替你翻译”原样保留。
给口播稿、拍摄导演表、剪辑交接单、素材清单和结构化 JSON。
不要假设自己能访问我的电脑；不能保存就输出可复制的全文。
原稿：……
```

如果使用的是“接入 DeepSeek 模型的 Agent”，由该 Agent 决定是否能安装技能、写文件和执行脚本。模型 API 的工具调用能力不等于聊天客户端自带这些工具；本包也不要求购买 API 或配置密钥。

## 7. 其他 Agent 与统一验收

支持标准 Agent Skills 的宿主加载 `skills/video-script-director/`，保留目录结构；`agents/openai.yaml` 是可选界面信息，非 Codex 宿主可以忽略。没有 Skill 功能就粘贴通用提示词。原生方式通常按需加载引用，文本方式把方法直接放进对话，二者使用相同创作规则。

无论使用哪个平台，先用 README 的 60 秒主题做一次试用，检查：

- 有完整可读的口播，不只给提纲。
- 时间段连续，未拍摄时标为预估。
- 具体写出哪里重读、停顿、举例、回应疑虑，以及表情和动作。
- 剪辑效果对应实际台词短语，注明第几次出现和何时恢复。
- 没有凭空补数据、实际图片或不存在的下载链接。

这些是使用后的检查点，不代表所有平台已经完成实测。文件输出、生图与剪辑执行由宿主能力决定。

## 常见问题

**只回了一个提纲？** 追加：“请按完整交付格式输出全部台词和导演表，不要只给建议；太长可以分文件连续输出。”

**说安装成功但找不到？** 检查最终路径是否直接包含 `SKILL.md`、名称是否为 `video-script-director`、是否启用。重新打开会话后再试；让助手直接读取本地文件可作为临时入口。

**没有 Python？** 正常写稿和导演设计不依赖 Python；脚本只是结构校验和导出助手。

**能直接一键剪成片吗？** 本 Skill 先交付导演方案。再把真实视频、`edit-brief.json` 与剪辑交接单交给具备剪辑工具的 Agent，由它对齐实录并执行。
