# 一份需求，一份本地任务记录

工具：`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/leanflow.py"`，以下以 `LF` 指代这条调用。
需 Python 3.9+、macOS/Linux；Git 项目共享根为 `git rev-parse --git-common-dir` 下的
`leanflow/`，通过 `LF locate` 解析，不能假定当前 `.git` 是目录。非 Git 项目使用
指定项目根的 `.leanflow/`。后来 git init 时，在 git add 前运行 `LF migrate`：停止其他
任务写入者，将整个目录原样迁入 Git common dir，保留正文、默认值、revision 和累计预算。
`locate` 只报告待迁移，其他操作会提示迁移，不能从空目录重建任务。目标目录已存在或记忆
已被 Git 追踪时拒绝移动，先核对并处理冲突；不覆盖或重置。迁移后按任务 id 恢复，旧绝对
路径不再有效。不自动清理 Git 历史；跨文件系统移动失败时保留原记录并报告。

## 定位与创建

- `LF list` 只列未完成记录，输出来源 worktree。优先明确指定的 id/绝对路径或当前上下文；
  无明确目标且当前 worktree 只有一个候选才自动选择。多个候选或仅有其他 worktree 的任务
  时让用户选择，不能把另一项任务的上下文猜成当前需求。
- `LF show <id>` 返回任务、实际 policy 和 revision；同一会话内容未变不重复读取。
  切换 worktree 时记录可读不等于代码也已转移，先核对分支、提交及未提交改动；
  代码不在此工作区时回到原工作区或按用户要求转移，不能直接重复实施。
- 新需求 `LF new <kebab-id> --title '<标题>' [--level high] --body -`，从 stdin 一次写入正文。
  不覆盖现存 id。记录原始目标、来源/非目标、重要决定、验收与任务、当前状态/下一步即可，
  有内容才增设小节；low 可以十几行。没有每项任务的固定数量要求。
- 每个需求只有 `tasks/<id>.md`；T1/T2、Review 轮次、Agent 不另建 plan、handoff 或日志文件。
  项目有跨任务稳定决定时才创建 `project.md`，不复制已有代码/文档，未经证实的猜测标明状态。
- Git 内的记忆天然不进入工作树索引；不 git add 记忆、自动导出或更改项目 .gitignore。
  不在命令外注入整份记忆，也不装 SessionStart/每工具调用记账 hook。

## 更新与恢复

- frontmatter 由工具管理：level、阶段、累计额度、revision、来源 worktree、基线。
  Markdown 正文是唯一的需求/计划/证据/恢复摘要，子 Agent 只回报，主协调者合并写。
- `LF checkpoint <id> --revision N --phase awaiting_uat --body -` 原子替换正文。
  只传 `--phase` 时保留正文。revision 取上次工具结果；冲突时重读、合并，不能盲目覆盖。
  `reserve`、`level` 等写操作也递增 revision。短暂锁使用目录本身，无常驻锁文件。
- 重要决定立即保存；其他在批次完成、等待或交接时合并更新。low 普通直通以初始化/交付
  两次写回为目标，有真正阻塞或中断可加一次，不能因节省写入丢失决定。
- 正文保留最新有效证据、遗留问题、关键失败原因与下一步，不逐条复制工具输出。
  完整日志/trace 由测试工具按需产生，正文只引用；测试代码属于项目资产。
- 一次完整修复循环结束时 `checkpoint --progress yes|no` 更新无进展计数，勿将单次工具
  调用计为一轮。只有实质进展/已有阻塞被新证据解除才能填 yes；续跑和升档不能清零。
- 多个主会话不要同时推进同一 task；先核对来源 worktree 与正在运行的协调者。
  原子更新/revision 防止记录覆盖，不代表代码工作区已隔离。

## 证据

每项检查记「范围、命令/环境、结果、对应代码状态」。可用 `LF fingerprint src tests
package.json pnpm-lock.yaml` 获取指定路径的内容指纹（包含未提交及未跟踪文件）。
路径相对仓库根；只传实际相关路径，子模块单独取证。HEAD 单独作为来源，不能单独证明
未提交代码。工具不检查运行时环境、外部服务或数据库，它们的变化也会使相关证据失效。
仅更新本地任务记录不会改变代码指纹。失败与待 UAT 不能用旧成功结果覆盖。

旧 plans 迁移、导出 docs 和项目默认设置，按需读 `commands/memory.md`。
