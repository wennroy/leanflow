---
description: 查看本地任务、设置项目默认档位，或将精选任务快照导出到 docs
argument-hint: "[list|show <id>|default <level>|migrate|export <id> [--to <docs/path.md>]]"
---

# /leanflow:memory

先确定 `<plugin-root>`：使用宿主给出的实际安装目录，或从本入口源文件/迁移 Skill 的祖先目录
查找 `.claude-plugin/plugin.json`（name=leanflow）与 `scripts/leanflow.py`。同会话核实后复用；
后文占位符替换成该绝对路径，不依赖 shell 中存在 `CLAUDE_PLUGIN_ROOT`。定位失败报告入口缺口，
不从其他源码目录猜测，不全盘搜索。

读取 references/memory.md；用 `<plugin-root>/scripts/leanflow.py` 操作，
不另建索引、摘要库或数据库。下面 LF 均指 `python3 "<plugin-root>/scripts/leanflow.py"`。

- 无参数/list → `LF list`，展示当前未完成任务及档位/阶段；要历史时用 `list --all`。
- show → `LF show <id>`，简短说明目标、状态、剩余问题与下一步。
- default → `LF default <level>`；自然语言「这个项目默认 low」同样处理。
  只修改 project.md 的默认值，已有任务继续使用自己保存的 level。
- migrate → 非 Git 项目初始化 Git 后，用 `LF migrate` 原样转移已有 `.leanflow/`，
  保留默认值、计数与正文；停止其他写入者，目标冲突时不覆盖。迁移后以原 task id 恢复。
- export → 读取任务，整理目标、关键决定、结果、验证摘要、遗留项为一份 Markdown；
  使用 `LF export <id> --summary - --to <绝对 docs 路径>` 从 stdin 传入。
  未指定位置则选 docs/leanflow/<id>.md；冲突选新名字，不覆盖。保留代码状态与证据限制，
  不复制原始日志、凭据、临时推理。工具写来源 task/revision/时间/HEAD，HEAD 不代替未提交
  代码证据。原任务继续保留；不自动 git add/commit，用户已要求提交时按该授权处理。
- 用户明确调整预算：`LF budget <id> --review N --agents N --reason '<授权与原因>'`，
  两个参数可分别设置。N 是累计上限，不是新增次数；不重置计数。无需新建配置文件。
  medium 起总派发默认只统计；设置 --agents N 后全部角色都占用这个总额度。
  用户要撤销总上限用 `LF budget <id> --agents unlimited --reason '<授权与原因>'`，
  不改变 Review 上限、累计次数或 low 的零 Agent 规则，不自动取消旧任务的显式总上限。

## 旧 plans 兼容（只有遇到旧记录时才读）

1. 本地没有明确目标时，检查用户指定的旧 plan 或 plans/ 下未完成条目；不自动重开 done/。
2. 读取原记录和已有 Git/会话证据，确定已使用 Review 与全部 Agent 次数及实施前基线。
   无法确认次数/基线时记录缺口，先完成无依赖工作；不能假定为 0 或用恢复时 HEAD 替代。
3. `LF import <id> --source <旧 plan 路径> --review-used N --agents-used N [--baseline <commit>]
   [--level medium]`。原文复制进唯一的本地任务，原文件保持原样；原 level 能明确确定时沿用。
   不传 baseline 就保留未知。工具导入后阶段为 plan，立即根据已完成证据 checkpoint 到
   实际阶段，并注明本地记录是之后的恢复依据；绝不把已有勾选当作全部待实现。
   后来找到真实基线时用 `checkpoint --revision N --baseline <commit>` 补全；已有基线不能覆盖。
4. 此后只维护本地记录，不同步两份执行状态。用户要更新/归档旧 Git 文档时用精选快照。

## 主协调者常用操作

```sh
python3 "<plugin-root>/scripts/leanflow.py" new login --level medium --body - <<'MD'
# 登录
目标：在已有登录页显示准确的失败原因。
验收：已知错误码有对应提示；未知错误有兜底提示。
下一步：实现并运行相关测试，随后集中 UAT。
MD
```

同一需求后续用 show/reserve/checkpoint 更新。正文可通过 stdin 传入，不创建临时交接文件。
交付 checkpoint 必须同时带 completion 定义的 --checks JSON；show/写回返回 delivery 的
完成条件和缺口，派发次数不是已完成审查次数。旧记录缺摘要时依据既有证据补齐，不重建任务。
frontmatter 使用 `key: JSON值` 的 YAML 子集，保持工具管理；不手动修改计数或复制出另一套状态。
工具在 macOS/Linux 对目录加短锁，checkpoint 还检查 revision；仅保障记录完整性，
不提供多会话代码调度。命令调用次数上限只能约束遵守 reserve 协议的 Agent，不能拦截宿主
在插件之外的调用。工具错误时保留原始状态，不静默重建；原生宿主工具不可用时如实报告。
