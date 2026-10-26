# 配置与授权

复制 `assets/research-radar.example.json` 到**用户项目**的 `research-radar.local.json`，不要把个人配置提交到技能仓库。

| 字段 | 用途 |
|---|---|
| `timezone` | 运行日期与检索区间使用的 IANA 时区 |
| `research_profile` | 每次重新读取的研究画像路径 |
| `daily_directory` / `template` | Daily 输出目录与现有模板 |
| `recommended_database` | 仅题录的历史推荐去重记录 |
| `sync_database` | Zotero 分类、条目与附件核验状态 |
| `note_directory` / `deep_read_template` | 精读笔记目录与模板，默认 `Note` / `Note/精读论文模板.md` |
| `reading_index` | 阅读面板位置，默认 `面板/_论文阅读索引.md` |
| `obsidian_project_path` | 相对整个 Obsidian 库的项目路径，库根目录项目填空字符串，用于 Wikilink |
| `zotero.collection_name` | 用户要求的分类；示例名称可修改 |
| `zotero.collection_key` | 初次解析并核验后记录的稳定 key |
| `zotero.data_dir` | 可选，用于本地 API 不可读时只读核验 |
| `zotero.auto_import` | 是否已有用户授权每日创建条目 |
| `downloads.main_pdf` / `include_si` | 下载范围；默认均为 `true`，正文与对应补充材料分别获取和核验 |

初次配置核对项目、分类及自动入库授权。若当前请求已经明确授权，不重复确认。示例的 `auto_import: false` 是避免把安装技能当成修改文献库的授权。

在已授权下载的任务中，未另定范围时同时尝试正文与对应SI。已有项目明确设置 `include_si: false` 时仍尊重该选择；用户改为需要SI时更新为 `true`，并同步项目模板和存在的旧任务提示词，保留其他配置及定时任务日程。正文已存在不代表SI已齐，按最新范围补核验；不因范围更新把历史“未读SI”笔记改成已读。

解析分类后同时核验文库和名称；同名分类歧义时请用户选择。不要写入示例中的其他用户 key，不把 collectionID 固定为跨设备配置。目标缺失时报告，除非用户也授权创建分类。

`Research Profile.md` 可包含研究问题、近期主题、方法、应用条件、排除项和价值判断。不要替用户编造画像。保留用户模板的 YAML、标题、Dataview 字段、标签和手动判断区；仅在初始化或用户要求修改时编辑模板。
