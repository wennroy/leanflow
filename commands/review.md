---
description: 派单个 reviewer subagent 审 feature 全量 diff：对照 plan 关键决定 + 代码质量，findings 分级输出
argument-hint: [plan 文件路径]
---

# /leanflow:review

对一个 feature 的全部改动做一次复审。spec 符合性和代码质量合并成
**一个 reviewer、看一遍**——不搞双 reviewer，不逐任务复审
（逐任务验收已由 verify 命令在 execute 阶段完成）。

## 0 · 定范围

- `$ARGUMENTS` 给了 plan 路径 → 用它；否则找 plans/ 里
  「状态：进行中」的 plan。
- 确定 diff 范围：该 feature 第一个任务提交之前 → 当前 HEAD
  （从 git log 找起点；分支开发就用 merge-base）。
  工作区未提交的改动也纳入。

## 1 · 派 reviewer

用 Agent 工具派**一个** leanflow:reviewer，prompt 含：

- diff 范围的说明（让它自己 git diff / git log 拿内容）
- plan 的「目标」「非目标」「关键决定」「假设」节原文
- 输出格式要求（结论 / 阻塞 / 建议 / 可选，见 agents/reviewer.md）

## 2 · 呈现与处置

1. findings **原样呈现**给用户，不加粉饰、不擅自过滤。
2. 用户逐条裁决：修 / 不修 / 记入 plan 后续做。
3. 判定要修的 → 内联修，修完跑相关 verify 或全局验收。
4. 全部处置完 → 「review 闭环，下一步 /leanflow:verify。」

禁止：擅自把 findings 全修了再问用户（裁决权在用户）；
发现 plan 外的"好想法"顺手做掉（记入可选档，不动手）。
