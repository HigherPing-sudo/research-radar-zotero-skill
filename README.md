# Research Radar + Zotero

读取最新研究画像，生成 Obsidian 每日论文推荐；按授权将文献保存到指定 Zotero 分类，获取合法可得的正文 PDF及对应补充材料，并在日报末尾提醒缺失项。

研究画像 → 多源检索 → 比较筛选与去重 → 每日分析 → Zotero 指定分类 → 正文附件核验 → Obsidian 阅读与跟进。

本仓库是 **agent 工作流 skill**。检索、Zotero 写入和下载由宿主 agent 的可用工具执行；Python 脚本提供只读检查、论文定位及日报回链。用户明确要求精读时，生成独立笔记并联动阅读索引。安装后先完成一次手动运行，再设置定时任务。

精读默认采用**原图配合详细讲解**：在方法与结果附近呈现关键原图，解释读图方法、公式算例和证据边界。已有笔记可增量补图，保留个人批注和阅读状态。版本变化见 [更新日志](CHANGELOG.md)。

## 使用导航

1. [准备运行环境](#1-准备运行环境)
2. [安装 Skill](#2-安装-skill)
3. [建立 Obsidian 目录](#3-建立-obsidian-目录)
4. [填写研究画像和配置](#4-填写研究画像和配置)
5. [首次运行与检查结果](#5-首次运行与检查结果)
6. [阅读和管理论文](#6-阅读和管理论文)
7. [设置每日定时任务](#7-设置每日定时任务)
8. [补做同步与更新配置](#8-补做同步与更新配置)
9. [常见问题](#9-常见问题)
10. [精读某天第几篇论文](#10-精读某天第几篇论文)

## 1. 准备运行环境

| 组件 | 用途 |
|---|---|
| 支持文件式 skill 的 agent，例如 Codex | 读取画像和模板、联网检索、写入 Markdown、执行同步 |
| Obsidian 本地库 | 查看日报、管理阅读进度和后续决定 |
| Zotero Desktop | 保存文献及正文附件，打开 `zotero://` 链接 |
| Zotero 工具或受支持的写入接口 | 新建条目、指定分类和保存附件；只读接口无法完成入库 |
| Python 3.10+（可选） | 运行仓库内的只读核验脚本，标准库即可 |
| PyMuPDF（配图提取时可选） | 将正文 PDF 的指定图区域渲染为 PNG；安装命令为 `python -m pip install PyMuPDF` |
| Dataview（可选） | 展示两个索引看板，普通日报阅读不依赖它 |

让 agent 能访问项目目录、所需 Zotero 接口与网络来源。采用本地数据库检查时，还需读取用户明确指定的 Zotero 数据目录；PDF 内容核验需要宿主具备 PDF 解析能力。

先在 Zotero 中准备目标分类，例如“我的文库 / 光谱分析”。其他研究方向可换成自己的分类名；同名分类存在多个时，先明确文库及完整路径。

## 2. 安装 Skill

推荐在 Codex 中发送：

```text
使用 $skill-installer，从 https://github.com/Heigherping/research-radar-zotero-skill
安装仓库根目录中的 skill，安装目录名使用 research-radar-zotero。
```

也可以下载 [Release 安装包](https://github.com/Heigherping/research-radar-zotero-skill/releases)，将 ZIP 内的 `research-radar-zotero` 文件夹放入当前宿主识别的 skills 目录。安装后应能找到：

```text
research-radar-zotero/
├─ SKILL.md
├─ agents/openai.yaml
├─ assets/
├─ references/
└─ scripts/zotero_inspect.py
```

Codex 的用户级手动安装目录可用 `~/.agents/skills/research-radar-zotero/`；Windows 对应 `%USERPROFILE%\.agents\skills\research-radar-zotero\`。通过内置安装器安装时，以其实际返回路径为准；已在 `~/.codex/skills/` 中正常发现的安装可以继续使用，避免重复安装同名 skill。若更新后未出现，重启 Codex。参见 [OpenAI 官方 Skill 文档](https://learn.chatgpt.com/docs/build-skills)。

检查能否选择或调用 `$research-radar-zotero`。安装 skill 本身不会创建定时任务或修改 Zotero。

## 3. 建立 Obsidian 目录

下列结构对应本项目的实际使用方式，路径已去除个人磁盘位置。`Research Radar` 可以是库内文件夹，也可以直接作为独立库的根目录。

```text
你的 Obsidian 库/
└─ Research Radar/                         ← agent 打开的项目目录
   ├─ Research Profile.md                  ← 用户维护的研究画像
   ├─ research-radar.local.json            ← 本机配置与已确认偏好
   ├─ Daily Papers/
   │  └─ YYYY-MM-DD.md                     ← 每天一篇，通常含 3 篇论文
   ├─ Template/
   │  └─ Daily Research Radar — YYYY-MM-DD.md
   ├─ Database/
   │  ├─ recommended.json                  ← 推荐历史，仅题录，用于去重
   │  └─ zotero-sync.json                  ← 分类、条目、附件及失败状态
   ├─ Note/
   │  ├─ 精读论文模板.md                    ← 模板，不计入阅读统计
   │  └─ YYYY-MM-DD-Paper2-论文题名.md      ← 按明确精读请求生成
   ├─ 面板/
   │  ├─ _Daily Papers 索引.md             ← 按“进一步阅读”等决定分类
   │  └─ _论文阅读索引.md                   ← 日报与精读笔记合并的状态看板
   └─ _论文阅读索引.md                      ← 可选，嵌入面板的快捷入口
```

把 [assets/daily-template.md](assets/daily-template.md) 复制为 `Template/Daily Research Radar — YYYY-MM-DD.md`。已有模板则优先保留原模板，再让 agent 补上 Zotero 链接与页末提醒字段。模板文件名中的 `YYYY-MM-DD` 是模板占位名称；实际日报输出为 `Daily Papers/2026-10-22.md` 这样的日期文件。

两个看板是可选项：

| 仓库模板 | Obsidian 中的位置 |
|---|---|
| [daily-decisions-index.md](assets/daily-decisions-index.md) | `面板/_Daily Papers 索引.md` |
| [paper-reading-index.md](assets/paper-reading-index.md) | `面板/_论文阅读索引.md` |

索引使用 DataviewJS，需要安装并启用 Obsidian 的 Dataview 插件及其 JavaScript 查询选项。两个模板顶部都有 `CONFIG`，将 `folder` 改为**相对整个 Obsidian 库根目录**的路径：

- 项目位于库内 `Research Radar/`：用 `Research Radar/Daily Papers`。
- 项目自身就是库根目录：用 `Daily Papers`。
- 决定索引还需同步修改 `jsonPath`，例如 `Research Radar/Database/recommended.json`。
- 阅读索引同时修改 `noteFolder`，例如 `Research Radar/Note`。

日常阅读不需要打开 JSON。首次缺少历史文件时，让 skill 初始化；已有文件保留原内容。仓库不包含用户的画像、日报或运行数据库。

## 4. 填写研究画像和配置

### 研究画像

在项目根目录创建 `Research Profile.md`。写清楚当前问题、已有条件和取舍；研究方向变化时直接更新此文件，每次运行都会重新读取。

```markdown
# Research Profile

## 当前研究问题
- 我正在解决什么问题？当前最需要哪些证据？

## 方法与技术
- 正在使用的方法、希望比较的替代方案、关键检索词。

## 应用与约束
- 样品或任务、可用仪器与数据、性能指标、工程限制。

## 推荐偏好
- 希望看到哪些方法改进、评估方案或可迁移思路？

## 排除项
- 哪些主题虽然关键词相近，但目前不需要？
```

画像应由用户提供真实内容。不要把示例问题当成研究事实；可先让 agent 整理已有材料，再核对。

### 本机配置

复制 [assets/research-radar.example.json](assets/research-radar.example.json) 到项目根目录，命名为 `research-radar.local.json`：

```json
{
  "timezone": "Asia/Shanghai",
  "research_profile": "Research Profile.md",
  "daily_directory": "Daily Papers",
  "template": "Template/Daily Research Radar — YYYY-MM-DD.md",
  "recommended_database": "Database/recommended.json",
  "sync_database": "Database/zotero-sync.json",
  "note_directory": "Note",
  "deep_read_template": "Note/精读论文模板.md",
  "reading_index": "面板/_论文阅读索引.md",
  "obsidian_project_path": "Research Radar",
  "zotero": {
    "collection_name": "光谱分析",
    "collection_key": null,
    "data_dir": null,
    "auto_import": false
  },
  "downloads": {
    "main_pdf": true,
    "include_si": true
  }
}
```

所有相对文件路径都以 **agent 打开的项目目录**为基准，与上面 Dataview 的库根目录基准不同。

- `collection_name`：改为目标分类。让 agent 查询并核验真实文库和 collection key，再保存 `collection_key`；不要复制其他用户的 key 或本机数字 collectionID。
- `data_dir`：可选的 Zotero 数据目录，来自 Zotero 设置中的真实位置，内含 `zotero.sqlite`。它不是程序安装目录或 Obsidian 附件目录。Windows 路径在 JSON 中可用 `D:/Zotero/data`，或对反斜杠写双重转义。
- `auto_import`：示例为 `false`。明确授权每日自动保存后，再由 agent 将确认后的偏好记为 `true`。
- `main_pdf` / `include_si`：示例默认同时获取正文与对应Supporting Information（SI）。保留用户明确的范围选择；用户修改后保存最新偏好，后续沿用。
- `timezone`：用于运行日期和检索时间窗口。09:30 等执行时刻由 Scheduled Task 管理。

完整字段说明见 [references/configuration.md](references/configuration.md)。

## 5. 首次运行与检查结果

在 Codex 中打开 Obsidian 的 `Research Radar` 项目目录，保持 Zotero Desktop 可用，发送以下提示词；分类名按需替换：

```text
使用 $research-radar-zotero，读取当前项目的 research-radar.local.json、
最新 Research Profile.md 和现有 Daily 模板，生成今天的论文推荐。
允许自动创建缺少的 Zotero 条目，并把新建和复用条目都加入
“我的文库 / 光谱分析”，保留条目原有的其他分类。
同时尝试正文 PDF 与对应补充材料（SI），分别核验并保存到同一父条目；已有可用附件直接复用。
首次核验目标分类后，将真实 collection key 和这些已确认偏好保存到本机配置。
在每篇简介中填写真实 Zotero 条目链接和本地 PDF 链接；
缺失 PDF、分类归入失败及其他待处理事项写在日报最后。
保留已有阅读状态、手动文字和复选框，不创建单篇永久笔记。
```

只想试用推荐、暂时不入 Zotero，可改为“仅生成推荐，不创建条目或下载附件”，并保持 `auto_import: false`。

一次完整运行会：

1. 读取最新画像、模板、推荐历史与同步记录。
2. 从最近一个月开始检索，相关证据不足时逐级扩展至 3/6/12/24/36 个月。
3. 比较候选后，默认推荐 2 篇高相关（可含一篇相关扩展）和 1 篇个性化热点；质量不足时少推。
4. 核验题录与版本关系，按 DOI、arXiv 等去重；明确分析基于摘要还是全文。
5. 创建当日日报，复用或创建 Zotero 条目，核验其确实属于指定分类。
6. 复用或尝试合法获取正文及对应SI；分别核验身份、文件角色及本地子附件，再写入链接。正文复用时也检查SI。
7. 更新历史与同步记录，在日报末尾汇总成功、缺失和失败。

首次运行后，检查以下结果：

| 位置 | 应能看到 |
|---|---|
| `Daily Papers/YYYY-MM-DD.md` | 题录、分析依据、中文简介、推荐理由、阅读判断区及页末同步结果 |
| Zotero 指定分类 | 对应文献；复用条目也属于该分类 |
| Zotero 文献下的附件 | 可在本机打开的正文PDF与对应SI；SI保留PDF、表格或ZIP等原格式，预印本回退有版本标注 |
| 日报的 Zotero 链接 | 可定位父条目；PDF 链接可打开对应附件 |
| 日报页末 | 逐篇列出需处理事项；全部完成时明确无需补充 |

“已创建条目”“已归入分类”“已保存正文”“补充材料状态”分别核验。正文成功但SI待处理时保留正文成功，并单列SI原因；只有官方已核实才写“未提供”。找不到PDF仍保留推荐与条目，只获取预印本时说明正式版尚未取得；下载不表示已经精读。

## 6. 阅读和管理论文

每篇简介都有两个 Zotero 入口：

```markdown
- **Zotero 文献:** [在 Zotero 中定位](zotero://select/library/items/PARENT_KEY)
- **Zotero PDF:** [在 Zotero 中打开 PDF](zotero://open-pdf/library/items/ATTACHMENT_KEY)
```

上例 key 仅用于解释格式，实际运行必须使用已核验的真实 key。父条目与附件使用不同 key；群组库使用对应 group URI。没有本地正文时显示缺失状态，不生成占位链接。

阅读后，在论文自己的 `### Paper N` 区块修改：

```markdown
- **阅读状态:** reading
```

可用 `unread`（未读）、`reading`（阅读中）、`done`（已读）。`面板/_论文阅读索引.md` 会按**每篇论文**汇总；存在精读笔记时优先取 Note 的有效状态，否则取日报的阅读状态。精读选择与笔记完成复选框的用法见[第10节](#10-精读某天第几篇论文)。

`Further Reading Decision` 用于另一种判断：

```markdown
- [x] 值得进一步阅读
- [ ] 加入待处理清单
- [ ] 暂不处理
- [ ] 需要先查看相关论文 / 补充材料
- **我的判断 / 下一步：** 先比较其预处理方法与当前基线。
```

`面板/_Daily Papers 索引.md` 按这些复选框分类；未勾选的归为“未决定”。阅读进度与后续处理决定相互独立。重跑同步会保留你的选择和文字。

看板依赖 `### Paper N`、`- **Title:**`、`- **阅读状态:**` 和复选框文本；修改这些结构时，相应调整看板解析规则。不要把仅扫描页面 frontmatter 的旧 `type: literature` 看板用于统计日报内的单篇论文。

## 7. 设置每日定时任务

确认手动运行及 Zotero 跳转都成功后，在该项目的桌面会话中发送：

```text
把当前 Research Radar 流程设置为每日 Scheduled Task，
每天 09:30，时区 Asia/Shanghai，在当前本地项目运行。
每次调用 $research-radar-zotero，并重新读取 research-radar.local.json、
最新研究画像、模板和历史；沿用已确认的指定分类、自动入库及正文与补充材料下载范围。
同日已有推荐时只补未完成的同步，保留人工判断。
如果已有同类任务，请更新它，避免重复创建。
```

09:30 是使用示例，可按需要调整。创建后核对项目、时间、时区与启用状态，并查看首次运行结果。后续修改时间，直接要求更新已有任务。

本流程需要本地 Obsidian 文件和 Zotero，应在可访问它们的本地环境运行；确保电脑开启、桌面宿主应用运行、项目可读写、Zotero 及所需网络可用。网页任务不能直接访问电脑上的文件夹。权限以宿主实际配置为准，定时运行不会自动获得额外权限。参见 [OpenAI 官方 Scheduled Tasks 文档](https://learn.chatgpt.com/docs/automations)。

## 8. 补做同步与更新配置

### 缺失 PDF 或接口恢复后重试

```text
使用 $research-radar-zotero，仅补做 Daily Papers/YYYY-MM-DD.md 中
尚未完成的 Zotero 分类归入、正文PDF与补充材料同步，不重新推荐论文。
先复查现有条目与附件，更新链接、同步记录和页末提醒，
保留阅读状态、复选框和我的文字。
```

把日期替换为实际日期。登录、验证码或机构访问需要人工处理时，先自行完成合法访问，再让 agent 继续。重试前会查询现有结果，避免请求超时后重复创建。

同日重跑也会核对日报与推荐历史；若日报已存在但历史漏记，按核验后的论文身份补齐题录，保留原有历史，避免之后再次推荐同一研究。

### 更换研究方向、模板或分类

- 研究方向：编辑 `Research Profile.md`，下一次运行读取最新内容。
- 日报布局：编辑项目内 Daily 模板，保留所需链接、阅读判断和提醒区；看板相关字段变化时同时调整索引。
- 更换分类：说明新文库与分类，让 agent 重新核验并更新配置中的名称和 key。不要只改名称却保留旧 key。
- 更换设备：安装 skill、迁移 Obsidian 项目，重新确认 Zotero 数据目录、文库、分类与本地附件；数字 collectionID 不能跨设备照搬。
- 更新 skill：更新安装目录中的公开文件，保留项目中的本机配置、画像、日报和历史；GitHub 更新不会自动同步到每台设备。

## 9. 常见问题

| 现象 | 检查与处理 |
|---|---|
| 看不到 skill | 核对安装目录和 `SKILL.md` 层级；检查是否被禁用，必要时重启宿主 |
| 推荐方向不符 | 更新画像的具体研究问题、约束与排除项，核对项目是否打开正确 |
| Zotero 有条目，目标分类没有 | 分类归属仍未完成；按页末提醒补做，不再次创建同一文献 |
| 没有下载 PDF | 查看失败阶段；来源不可用、权限不足或附件保存失败都可能导致缺失 |
| 只有 arXiv 预印本 | 保存并标注版本，同时提醒正式版缺失 |
| Zotero 链接打不开 | 确认本机 Zotero 可用、协议可调用、key 真实且属于当前文库；PDF 要有本地附件 |
| 看板为空或不执行 | 检查 Dataview 与 JavaScript 查询选项、库相对路径和 `### Paper N` 等字段 |
| 阅读状态数量不对 | 使用按论文区块解析的模板，避免只按日报 frontmatter 统计 |
| 本地 API 不可读或返回 403 | 核对接口能力；可配置真实数据目录做只读检查，写入仍需可用接口 |
| 定时任务没产出 | 查看任务状态与日志，确认时间、时区、本地项目、应用运行状态和权限 |

可在 **skill 安装目录或仓库根目录**运行只读诊断：

```text
python scripts/zotero_inspect.py status
python scripts/zotero_inspect.py inspect --data-dir <Zotero数据目录> --collection-name <目标分类> --doi <论文DOI>
```

将尖括号替换为实际值，含空格路径加引号。脚本读取数据库与 WAL 的临时一致快照，不写原库。题名匹配仅产生候选；文件存在、PDF 文件头正确也不等于论文内容已核验。无法可靠查询时记录“未核验”，不据此认定未收录。

## 10. 精读某天第几篇论文

将 [deep-reading-template.md](assets/deep-reading-template.md) 复制到 `Note/精读论文模板.md`，将新版 [paper-reading-index.md](assets/paper-reading-index.md) 放到 `面板/_论文阅读索引.md`。根目录需要快捷入口时，可嵌入 `![[Research Radar/面板/_论文阅读索引]]`；项目就是库根目录时去掉 `Research Radar/`。

模板包含文献与 Zotero 入口、问题与研究路径、方法、公式算例、实验设计、逐图表证据、局限、与研究画像的联系、复现计划及个人批注。模板按 `type: literature-template` 排除，不计入阅读统计。

有关键图的论文默认把原图嵌在相应讲解旁。方法图会解释输入、输出和模块关系，实验图会解释坐标、图例、分母、对照及失败情况；公式先讲用途，再用小数值算完。讲解采用易懂中文，保留必要技术术语，并分清原文结果、教学例子与项目建议。图表证据表继续保留，图片另存 `Note/Attachments/<论文标识>/`，标注图号、PDF页序与原文入口。提取后实际查看，确保文字清楚、坐标/图例完整、嵌入路径有效；额外SI仍沿用用户选择的范围。

也可以发送“给以前的精读补上原文图片，并讲得详细、通俗一些”。流程会读取已有笔记，增补对应章节并保留正文、个人批注、复选框和原阅读日期。完整约定及可选提取助手见 [图文精读与增量更新](references/illustrated-reading.md)。该助手依赖PyMuPDF，只负责指定区域渲染及来源清单；图号选择、读图与笔记讲解仍由agent完成。

准备好后直接发送：

```text
精读 2026-10-22 的第 2 篇论文，按我的精读模板生成笔记。
```

也可说“精读今天第 1 篇”或“讲透昨天的 Paper 3”。Skill 会按配置时区解析相对日期；日期或编号无法唯一确定时再澄清。完整流程见 [deep-reading.md](references/deep-reading.md)。

执行时会：

1. 精确定位 `Daily Papers/日期.md` 的 `### Paper N`，核对题名、DOI/arXiv 与真实 Zotero 条目。
2. 找到并读取对应本地 PDF；说明正式版/预印本和实际读到的范围。
3. 普通精读优先调用环境中可用的 `nature-paper-xray`，按其方法理解论文，再填入用户模板；明确要求 Paper Card 或双语阅读时选择相应 skill。未安装增强 skill 时使用内置流程。
4. 生成 `Note/2026-10-22-Paper2-论文题名.md`。文件名使用推荐日，`read_date` 记录执行日；非法字符替换，过长题名缩短，完整题名保留在属性中。
5. 在原日报对应论文中加入精读笔记回链；阅读面板同时显示日报、精读笔记及 Zotero 文献/PDF 入口。

`note_directory`、`deep_read_template` 和 `reading_index` 均以项目为路径基准；`obsidian_project_path` 以整个 Obsidian 库为基准，项目位于库根目录时填 `""`。

生成后的关键属性示意：

```yaml
type: literature
template: false
title: "完整论文题名"
source_date: "2026-10-22"
paper_number: 2
source_daily: "[[Research Radar/Daily Papers/2026-10-22#Paper 2]]"
read_date: "2026-10-22"
status: reading
analysis_status: complete
```

日报每篇论文的阅读状态旁有 `- [ ] 进行精读`：勾选为“是”，未勾选为“否”。阅读索引同步显示“是否精读”与已选数量；选中但尚无笔记时显示“待生成”。这是独立的阅读意愿，勾选不会立即生成笔记或改变阅读进度，仍需明确请求精读。旧日报没有该选项时，有真实精读笔记显示“是”，否则显示“未选择”。

`status` 是你的阅读进度：`unread / reading / done`。实际精读笔记（`type: literature`）勾选属性 `template` 后，面板优先归入“已读”；取消勾选后按原 `status` 显示。保留这个现有复选框名以兼容已创建笔记，它不会让真实笔记被当成模板忽略。有笔记时使用其有效状态并把同一日报论文合并为一行；没有笔记时沿用日报状态。修改日报选项或 Note 属性后面板自动更新，不回写文件。`analysis_status` 记录笔记生成进度，完成生成不等于你已读完。资料不足时标 `source_limited`，保留待补内容。

重复请求会更新已有笔记，保留个人批注、状态和复选框。同一日期/编号对应多个笔记、题名不一致或已有回链冲突时会提示核对。每日定时推荐保持原流程，只有明确要求精读时才生成单篇笔记。

精读笔记末尾“我的批注与下一步”提供 `- **评论判断：**`。在冒号后写自己的阅读感受、当前帮助或是否继续跟进，可接着换行写正文；下一条列表项或标题表示该栏结束。阅读索引的“评论判断”列自动读取并显示，空白显示“未填写”，也兼容旧笔记的“我的判断”。AI首次生成留空，重跑保留用户文字；评论独立于阅读状态，不因填写评论自动标为已读。

直接指定或自主添加的精读笔记不需要编造日报编号：没有日报来源时保留空的 `source_date/source_daily` 与 `paper_number: 0`，使用真实 `read_date`。两个面板会收录这类 `type: literature` 笔记；决定索引单列“自主精读”，阅读索引显示精读日期、状态、Zotero及评论。日报勾选“暂不处理”的论文在阅读索引中隐藏并排除统计，取消后恢复；决定索引保留相应分类供管理。

定位与回链助手（在 skill 安装目录执行）：

```text
python scripts/reading_target.py resolve --project <项目目录> --date 2026-10-22 --paper 2
python scripts/reading_target.py link --project <项目目录> --date 2026-10-22 --paper 2 --note "Note/实际笔记文件名.md"
```

`resolve` 只读，不生成笔记；`link` 仅在真实笔记已经生成、身份核验通过后添加日报回链。论文理解与笔记正文由 agent 执行。

## 开发验证与隐私

```text
python -m unittest discover -s tests -v
node tests/test_reading_index.cjs
node tests/test_decisions_index.cjs
python -m compileall -q scripts
```

仓库仅发布通用 skill、模板、配置示例和检查脚本。个人研究画像、实际配置、文库 ID、历史推荐、登录凭据及论文文件留在用户项目，不随公开包发布。目标项目若另外使用 Git，也需自行排除这些运行数据；本仓库的 `.gitignore` 不会自动作用于其他项目。

下载仅使用合法可访问来源；找不到就报告，不承诺每篇都有正文。每日推荐不会自动创建单篇笔记；明确精读请求才会生成，也不会替用户勾选阅读结论。

MIT License。Zotero、Obsidian 与 Codex 为其各自权利人的产品，本项目不是官方插件。
