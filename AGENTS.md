# Research Radar + Zotero skill

## 项目与目录

此目录是独立的公开 skill 仓库。目标是连接论文推荐、Zotero 资料保存和 Obsidian 精读。宿主 agent 执行检索与同步，仓库脚本负责只读核验、定位、回链与图片提取。

- `SKILL.md` 与 `references/` 定义工作流。
- `assets/` 存放通用模板和配置示例。
- `agents/` 存放宿主界面配置。
- `scripts/` 存放 Python 助手，`tests/` 存放 Python 与 Node.js 测试。
- 个人画像、实际配置、日报、文库与附件位于仓库外的用户项目，由该项目自行保存和备份。

## 长期规则

- 发布内容保持通用，个人数据按 `.gitignore` 排除。
- Zotero 数据库助手读取一致快照。文库写操作由宿主使用受支持接口执行。
- 回链通过同目录随机临时文件暂存，使用排他创建，关闭句柄后检查日报是否变化，再原子替换。失败时清理本次临时文件。
- 保留日报编码、换行、人工判断与幂等行为。临时文件安全修改需要覆盖预占链接、失败清理和并发编辑测试。

## 验证入口

在仓库根目录执行。

```text
python -B -m unittest discover -s tests -v
node tests/test_reading_index.cjs
node tests/test_decisions_index.cjs
git diff --check
```

Python 助手需要 Python 3.10+。图像提取测试使用已安装的可选 PyMuPDF。测试生成隔离临时项目，文件替换权限受沙箱限制时使用受支持的执行权限重试。

## 当前状态

2026-11-24 安全修复可直接实施。已将 `reading_target.py` 的固定 `.pending` 写入改为标准库 `NamedTemporaryFile`，保持同目录原子替换。

旧代码已通过新增回归测试复现项目外硬链接目标被覆盖及替换失败遗留临时文件。修复后完成硬链接保护、失败清理和暂存期间并发编辑保护的验证。

本轮源码、测试和记录采用同一本地提交管理，使用用户确认的仓库级 Git 身份。GitHub 版本发布状态以远程核验为准。

## 修改记录

| 日期 | 修改内容与文件 | 验证结果 | 剩余事项 |
| --- | --- | --- | --- |
| 2026-11-24 | `scripts/reading_target.py` 安全暂存与失败清理，`tests/test_reading_target.py` 增补回归，更新 `CHANGELOG.md` 与本文件 | 旧版两项回归失败，修复后 35 项 Python 测试、36 项阅读索引场景及决定索引测试通过，`git diff --check` 通过 | 按用户后续授权同步 GitHub 与发布版本 |
