---
name: leanflow-router
description: Use when the user asks to implement a multi-step feature, large
  refactor, or migration spanning multiple files — suggests leanflow workflow
  commands. Do NOT use for questions, small fixes, single-file changes, or
  exploratory/debugging tasks.
---

# Leanflow Router

判断用户请求是否是**多步骤、多文件的功能开发或重构**。

## 如果是

用一句话建议：「这个需求适合先 `/leanflow:plan` 出方案，也可以直接开始，你定。」

然后**无论用户是否采纳，继续正常工作**。铁律：

- 同一会话只建议一次，不重复提醒。
- 用户拒绝或无视 → 按用户的方式直接执行，绝不再提。
- 不存在"必须先 plan 才能写代码"的规定，不阻止任何工作。

## 如果不是（提问、小修、单文件变更、探索/调试）

不产生任何输出。
