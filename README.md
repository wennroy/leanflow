# leanflow

A lean workflow plugin for Claude Code — an explicit-invocation alternative to heavyweight process plugins (superpowers-style), designed for large features and refactors.

**核心理念**：把"强制链路"换成"显式调用"。所有流程由 `/leanflow:*` 命令显式启动；零 SessionStart 注入；确定性命令替代逐任务 LLM 复审。

## Design principles

1. **零注入** — 没有 SessionStart hook、没有 bootstrap 全文。always-on 成本 ≈ 几行 description（~300 tokens），对比 superpowers 6.2 实测 ~4k/session。
2. **显式调用** — 流程逻辑写在 command 正文里，只在调用时加载（单次 ≤4k tokens）。
3. **确定性验收** — plan 里每个任务带 `verify:` 命令，跑命令不花 token；LLM reviewer 只在最后看一次全量 diff。
4. **批量交互** — 澄清用决策树分轮：每轮把整个边界层一次问完、每题附推荐答案（可回「都按推荐」快进）；事实自己查，只把决定留给用户。
5. **状态在盘上** — `plans/<feature>.md` 的 checkbox 即进度，/compact 或跨会话后 `/leanflow:execute` 重读 plan 接着跑。

## Contents

| 组件 | 说明 |
|---|---|
| `skills/router` | 唯一的自动触发件：检测到大型功能请求时建议一次 `/leanflow:plan`，绝不 nag、绝不阻止工作 |
| `commands/plan` | 分轮批量澄清 → 代码勘察 → 落盘 plan（关键决定 / 假设 / 每任务 verify 命令） |
| `commands/execute` | 内联优先执行；连续 ≥2 个独立任务打包给 1 个 implementer；checkbox 断点续跑 |
| `commands/review` | 单个 reviewer subagent 审全量 diff（spec+质量合并，findings 三级） |
| `commands/verify` | 终检清单：全局验收、调试残留、非目标核对、关键决定对照 |
| `commands/finish` | 归档 plan、整理提交、可选 PR |
| `commands/debug` | 一页纸调试：复现 → 最小化 → 假设 → 修根因 → 回归 |
| `agents/implementer` | 隔离 context 承接打包任务，回报格式固定（≤60 行） |
| `agents/reviewer` | spec 符合性 + 代码质量一次看完，阻塞/建议/可选三档 |
| `hooks/` | Stop→项目 `.claude/verify.sh`（成功静默，失败截断输出，同样失败不重复阻断）；PreToolUse→危险命令护栏 |

## Install

```bash
# 添加 marketplace
claude plugin marketplace add wennroy/leanflow

# 安装
claude plugin install leanflow@leanflow
```

也可在 Claude Code 内通过 `/plugin` 交互界面完成。

## Hooks 说明

**Stop hook（验证）** 采用约定式启用：在项目根创建 `.claude/verify.sh` 即生效
（例如 `#!/bin/sh\npnpm typecheck && pnpm lint`）。不存在则完全静默。
成功时零输出；失败时把末 100 行喂给模型继续修；同样的失败只报一次。

**PreToolUse hook（护栏）** 只拦灾难性操作：`rm -rf` 根/家/当前目录、
force push 到 main/master、`git clean -f`、丢弃全工作区改动、dd/mkfs 等。
放行时零输出。

## Workflow at a glance

```
/leanflow:plan 加用户积分系统              # 分轮澄清 → plans/add-user-points.md
/leanflow:execute plans/add-user-points.md  # 内联执行 + 打包派发 + 每任务 verify
/leanflow:review                           # 单 reviewer 审全量 diff
/leanflow:verify                           # 终检清单
/leanflow:finish                           # 归档 + 可选 PR
```

## License

MIT
