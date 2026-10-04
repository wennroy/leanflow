---
description: 单独核对任务的分档验证证据与验收缺口，不触发完整开发流程
argument-hint: [任务 id/路径或改动范围]
---

# /leanflow:verify

按 references/memory.md 定位已有任务，读取 references/completion.md 的「验证」；
路径相对 `${CLAUDE_PLUGIN_ROOT}`。无任务时直接核对明确的改动范围，不强制建 plan。
有任务时遵循保存的 level，已有证据有效就复用，只补缺失/失效检查；用户明确重跑时遵从。

报告通过、失败、未验证、不适用、待人工确认及依据。low 不因调用 verify 就启用
Playwright 或 Review。需要 high 以上的独立测试时按预算和 tester 规则补充，不无限派发。
修改代码遵从已有修复授权；无授权则列出问题。该命令不自动完整复审、归档或发布，
也不把命令结束等同于整个需求完成。
