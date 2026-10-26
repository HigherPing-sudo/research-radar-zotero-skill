# Zotero、分类、正文与补充附件

## 读取与去重

优先使用当前环境可用的 Zotero 工具/本地 API。接口能力随版本不同，从响应确认实际可用能力；不假设 Local API 永远只读或永远可写。不要为自动化强制杀死 Zotero。

API 不可读时，`scripts/zotero_inspect.py` 可从用户明确指定的数据目录只读核验。它复制数据库与存在的 WAL，复制前后核对源文件状态，再在临时快照上查询；不直接写原库。数据目录应来自用户配置/实际设置，不能使用碰巧存在的旧数据库。无法可靠查询时停止创建，避免重复。

脚本返回匹配依据、候选条目、分类成员关系和 PDF 附件 key。标题匹配只能作为候选；需核对作者/年份。多个候选不自动合并。

## 写入与固定分类

确认用户已授权自动保存推荐。按 collection key 核验文库和名称；尚未配置 key 时，由已确认文库与无歧义分类名称解析。

新建与复用条目都应属于指定分类。复用条目添加成员关系时保留其他分类；不得为进入新分类重复创建同一文献。通过受支持 API/工具操作，不写 SQLite。

Connector 当前保存目标与指定分类可能不同，不能把 `collections` 放进任意 payload 就认为已生效。已确认的 Connector 流程可使用保存会话，再通过 `/connector/updateSession` 指定目标（`C<当前本机collectionID>`），最后读取实际成员关系。数字 ID 须在当前实例解析。新增项创建前核对当前文库，不能先误写到其他群组。

写响应不确定时先重新查询；不要重复创建。现有条目的分类添加若没有可用接口，报告 `collection_pending`，不把它算成功。

## 合法 PDF 获取

只处理最终推荐。复用已有可读正文；缺少时优先出版社正式版，再检查机构/作者仓储、PMC 或 arXiv。用户已有合法机构访问或出版商授权可用时，通过实际受支持路线获取。

不绕过付费墙、验证或权限。无人值守遇认证/验证码记录待用户处理并继续。正文 PDF 与 SI 分开；按确认偏好下载，不把 SI 当作正文。

检查 PDF 文件头，然后用可用解析库确认非空页数，并核对首页标题/作者/DOI。登录页、HTML、空文件和错误论文均不算成功正文。

保存为父条目的本地存储型子附件；仅有 URL、网页快照或附件记录不等于本地 PDF。复查附件 key、父条目关系和文件可读性。通过 Connector `saveAttachment` 上传时，关联的是已有保存会话的 connector item ID；先核实该版本接口契约。无上传能力就报告，不改写底层数据库。

```text
zotero://select/library/items/PARENT_KEY
zotero://open-pdf/library/items/ATTACHMENT_KEY
zotero://select/groups/GROUP_ID/items/PARENT_KEY
zotero://open-pdf/groups/GROUP_ID/items/ATTACHMENT_KEY
```

群组 URI 使用外部 group ID，不是内部 libraryID。仅填真实 key。预印本回退在附件名称和 Daily 注明，不能宣称取得最终版。

## 对应补充材料（SI）

已授权下载时，默认 `downloads.include_si: true`；项目明确选择关闭则按其选择。用户更新范围后以最新配置为准。只处理最终推荐或明确指定的论文，不扩展成候选池、整站或外部数据仓库批量下载。

1. 即使复用了正文，也检查对应版本的出版社文章页、Supporting Information/Supporting Data入口、官方Figshare或PMC等补充文件清单。核对关联DOI、题名、作者与版本；没有找到不等于官方未提供，未核实也不等于下载失败。
2. 逐份获取列出的附属材料，保留原格式与文件名含义，包括补充PDF、XLSX/CSV、图像或ZIP等。仅给出的独立大型代码/数据仓库入口先记录，不把它解释成下载整个仓库的指令。权限或来源受限时记录具体入口、原因和待处理项。
3. PDF检查可读页数及材料身份；非PDF检查真实格式、非空内容及来源关联，ZIP可查看文件清单而不执行内容。拒绝登录/错误页面，不把Excel、ZIP等强行改名成PDF。正文与SI角色单独核实，正文链接始终指向真实正文。
4. 为同一父条目分别保存本地存储型子附件，名称说明“补充材料/SI”和文件角色。已有附件按来源、名称及内容哈希核对后复用，保留用户命名及标注；不能因正文和SI共用DOI就把不同文件合并。保存后逐份核验附件key、父条目、文件可读性，生成该格式适用的真实入口；非PDF可给Zotero附件定位链接。
5. 在同步记录中保留补充文件清单，每份记录来源URL、角色/格式、版本、附件key、内容核验状态与错误摘要。正文状态与SI状态独立；日报说明已存、复用、失败/待核验，只有已查官方页面确认无SI才标“官方未提供”。下载已完成仍不表示精读已阅读，应在笔记里另记实际阅读范围。

`zotero_inspect.py`返回PDF附件候选和文件头检查，不区分每份正文/SI的语义，也不核查全部非PDF补充文件；`reading_target.py`只沿既有正文key定位。必须实际识别正文角色，并另行核验SI清单，不能把助手结果当成补充材料全部完成。

## 状态与重跑

每项记录论文身份、条目 key、目标 collection key、分类归属核验状态、附件 key、版本、来源、核验日期及错误。完成需同时满足条目存在、目标分类归属成立、本地正文可读；预印本可标 `complete_with_preprint`，同时提示最终版缺失。

启用SI时还需核对当前补充文件清单：已识别材料均已保存并核验，或官方明确没有提供，才算当前下载范围全部完成。正文成功、SI失败或未知时分别保留正文成功与SI待处理，不把全部同步写成完成。旧记录只核验过正文时，按新范围补SI，不重新创建条目或正文，也不回填虚构的历史下载/阅读结果。

重跑只补未完成环节，不重新推荐，不重复附件，不覆盖人工判断。临时下载仅在导入核验成功后清理；失败时报告可恢复中转位置。

## 官方接口资料（能力不一致时查阅）

- [Zotero Local API](https://www.zotero.org/support/dev/web_api/v3/local_api)
- [Connector HTTP Server](https://www.zotero.org/support/dev/client_coding/connector_http_server)
- [Connector 实现](https://github.com/zotero/zotero/blob/main/chrome/content/zotero/xpcom/server/server_connector.js)
- [条目附件与本地存储](https://www.zotero.org/support/attaching_files)
- [Zotero URI 与附件 key](https://forums.zotero.org/discussion/90858/pdf-reader-and-zotero-open-pdf-links)
