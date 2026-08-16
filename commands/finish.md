---
description: 收尾：归档 plan、整理提交、可选建 PR
argument-hint: [plan 文件路径]
---

# /leanflow:finish

收尾一个已完成并通过终检的 feature。

## 步骤

1. **确认前置**：plan 全部勾选、终检已过；有未提交改动先问用户。
2. **归档 plan**：把「状态」改为「已完成」，移到 `plans/done/`
   （目录不存在就建）。
3. **整理提交**：用 git log 展示本 feature 的提交序列；
   要不要 squash / 改 message 由用户决定，不擅自 rebase。
4. **PR**：用户明说才建。`gh pr create`，body 用 plan 的
   「目标」「关键决定」生成，附上验证结果。
5. 一句话收尾：「feature 完成，plan 已归档到 plans/done/。」

禁止：擅自 push、擅自 merge、擅自删分支——这些动作都要用户明说。
