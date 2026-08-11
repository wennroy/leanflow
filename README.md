# leanflow

A lean workflow plugin for Claude Code — an explicit-invocation alternative to heavyweight process plugins (superpowers-style), designed for large features and refactors.

**核心理念**：把"强制链路"换成"显式调用"。所有流程由 `/leanflow:*` 命令显式启动；零 SessionStart 注入；确定性命令替代逐任务 LLM 复审。

## Design principles

1. **零注入** — 没有 SessionStart hook、没有 bootstrap 全文。always-on 成本 ≈ 几行 description（~300 tokens），对比 superpowers 6.2 实测 ~4k/session。
2. **显式调用** — 流程逻辑写在 command 正文里，只在调用时加载（单次 ≤4k tokens）。
3. **确定性验收** — plan 里每个任务带 `verify:` 命令，跑命令不花 token；LLM reviewer 只在最后看一次全量 diff。
4. **批量交互** — 澄清问题用 AskUserQuestion 一轮问完；需求模糊时出"假设驱动"的 plan，改 plan 比答问题快。
5. **状态在盘上** — `plans/<feature>.md` 的 checkbox 即进度，/compact 或跨会话后 `/leanflow:execute` 重读 plan 接着跑。

## Contents

| 组件 | 状态 | 说明 |
|---|---|---|
| `skills/router` | ✅ | 唯一的自动触发件：检测到大型功能请求时建议一次 `/leanflow:plan`，绝不 nag、绝不阻止工作 |
| `commands/plan` | 🚧 | 批量澄清 → 落盘 plan（每任务带 verify 命令 + 「假设」节） |
| `commands/execute` | 🚧 | 内联优先执行；相邻 ≥2 个独立任务打包给 1 个 implementer |
| `commands/review` | 🚧 | 单个 reviewer subagent 审全量 diff（spec+质量合并） |
| `commands/verify` | 🚧 | 全局验收命令 + 收尾清单 |
| `commands/finish` | 🚧 | commit / PR / 归档 plan |
| `commands/debug` | 🚧 | 精简调试流程：复现 → 最小化 → 假设 → 修 |
| `agents/implementer` | 🚧 | 隔离 context 承接打包任务，回报格式固定 |
| `agents/reviewer` | 🚧 | spec 符合性 + 代码质量，findings 分级 |
| `hooks/` | 🚧 | Stop→项目 `verify.sh`（失败才输出）；PreToolUse→危险命令拦截 |

## Install

```bash
# 添加 marketplace
claude plugin marketplace add wennroy/leanflow

# 安装
claude plugin install leanflow@leanflow
```

也可在 Claude Code 内通过 `/plugin` 交互界面完成。

## Workflow at a glance

```
/leanflow:plan 加用户积分系统        # 出 plans/add-user-points.md
/leanflow:execute plans/add-user-points.md   # 内联执行 + 打包派发 + 每任务 verify
/leanflow:review                    # 单 reviewer 审全量 diff
/leanflow:verify && /leanflow:finish
```

## License

MIT
