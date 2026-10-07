---
description: 单独核对任务的分档验证证据与验收缺口，不触发完整开发流程
argument-hint: "[任务 id/路径或改动范围]"
---

# /leanflow:verify

先确定 `<plugin-root>`：使用宿主给出的实际安装目录，或从本入口源文件/迁移 Skill 的祖先目录
查找 `.claude-plugin/plugin.json`（name=leanflow）与 `scripts/leanflow.py`。同会话核实后复用；
后文占位符替换成该绝对路径，不依赖 shell 中存在 `CLAUDE_PLUGIN_ROOT`。定位失败报告入口缺口，
不从其他源码目录猜测，不全盘搜索。

按 references/memory.md 定位已有任务，读取 references/completion.md 的「验证」；
路径相对 `<plugin-root>`。无任务时直接核对明确的改动范围，不强制建 plan。
有任务时遵循保存的 level，已有证据有效就复用，只补缺失/失效检查；用户明确重跑时遵从。

报告通过、失败、未验证、不适用、待人工确认及依据。low 不因调用 verify 就启用
Playwright 或 Review。需要 high 以上的独立测试时按预算和 tester 规则补充，不无限派发。
有任务时核对 completion 的四项交付摘要与 delivery 缺口；派发次数和 awaiting_uat 阶段
都不能证明验收通过。medium 默认无浏览器检查，未覆盖的原故障路径明确留 UAT。
修改代码遵从已有修复授权；无授权则列出问题。该命令不自动完整复审、归档或发布，
也不把命令结束等同于整个需求完成。
