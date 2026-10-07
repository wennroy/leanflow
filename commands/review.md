---
description: 对指定任务或 diff 独立复审，按累计预算处理 findings 与定向复核
argument-hint: [--level <level>] [任务 id/路径或 diff 范围]
---

# /leanflow:review

先确定 `<plugin-root>`：使用宿主给出的实际安装目录，或从本入口源文件/迁移 Skill 的祖先目录
查找 `.claude-plugin/plugin.json`（name=leanflow）与 `scripts/leanflow.py`。同会话核实后复用；
后文占位符替换成该绝对路径，不依赖 shell 中存在 `CLAUDE_PLUGIN_ROOT`。定位失败报告入口缺口，
不从其他源码目录猜测，不全盘搜索。

按 references/levels.md、references/memory.md 定位范围与预算，使用
references/completion.md 的证据和处置规则；路径均相对 `<plugin-root>`。

## 范围与预算

- 有任务时以记录的实施前基线、用户需求和全部本次 diff 为依据，含暂存/未暂存/未跟踪。
  已有有效复审直接复用，用户明确重审或相关变化才扩大范围。
- 无任务也可审用户指定 diff 或当前改动，需求不明的部分报告限制，不虚构验收依据。
  独立调用无需强建 plan：按显式 level 或项目默认（缺省 medium）在当前调用内计数；
  需要跨会话持续修复才保存为一项本地任务，带入已用次数，不从零开始。
- 参数指定 low 与独立 Review 请求冲突时说明冲突，让用户选择 medium 以上或取消；
  execute 的 low 不进入本命令。不可偷偷升档。
- 对有任务的每次首审/复核，先 `reserve <id> reviewer` 再派发；无任务也遵守相同上限。
  额度不足或独立 Agent 不可用，保留待复审缺口，不能冒充通过。

## 一次完整首审，随后定向复核

读取 agents/reviewer.md；提供范围/基线、原始需求、关键决定、验收及对应代码证据。
reviewer 只读，合并检查需求符合性和代码质量。每条 finding 都保留判断和处置，
有证据的范围内 bug 在 execute 已有实施授权下自动修；范围/产品决定集中问用户。
独立 review 默认报告，只有用户已要求修复才改代码，不由一次审查请求推导额外修改授权。

修复后跑受影响验证，用 reviewer 复核原问题及受影响部分；复用原 reviewer 的上下文也
消耗一次调用预算。首审无问题且证据有效可结束，不为用完轮数再审一次。
同一类无进展循环按 levels 停止，不用新 Agent 重新开始计数。

报告已修复、不成立（附理由）、已接受遗留、待决定/待复核和验证限制。
内部调用返回 execute/finish，独立调用不自动归档或再调用 verify/finish。
