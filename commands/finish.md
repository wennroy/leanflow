---
description: 从已有本地任务继续验收与交付收尾，沿用档位和累计预算
argument-hint: [任务 id/路径]
---

# /leanflow:finish

日常 execute 已包含收尾，本入口供只差验收或交付的任务使用。
读取 `${CLAUDE_PLUGIN_ROOT}/references/memory.md` 和 `references/completion.md`。

1. 按 memory 规则定位任务，旧 plans 先按 commands/memory.md 迁移。done 的任务只报告已有结果。
2. 核对当前代码与已有证据。尚未实施的范围说明需继续 execute，不擅自扩大成新功能开发。
3. 缺少必要验证/复审时遵循保存的 level 和累计预算补缺口；low 不派 reviewer/tester，
   high 以上缺独立测试按 agents/tester.md 执行，缺复审按 commands/review.md 执行。
   没有额度或能力时如实记录待办，不默认重复完整流程。
4. 集中处理待决定/UAT。用户只确认部分就只更新对应项；代码未变的 UAT 确认直接收尾。
5. 满足 completion 条件原地标 done，不自动复制到 docs 或移动到 plans/done。
   Git 批次提交沿用已获授权；push/PR/部署等动作仍按用户要求。

报告交付结果、证据、遗留项、本地记录与 Git 状态；导出正式文档使用 memory export。
