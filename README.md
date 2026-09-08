# leanflow

A lean, explicit-invocation workflow plugin for Claude Code.

日常使用两个命令：**plan 明确方案，execute 完成实施、验证、一次独立复审与验收归档**。
保持 `commands/`、`agents/`、`hooks/` 和 `skills/router/` 的 Claude Code 插件组织。

## Design principles

1. **按需加载** — 没有 SessionStart 注入；router 只建议一次，用户可直接工作。
2. **显式调用** — plan 只产出方案；execute 启动完整执行流程，用户可以要求停在指定阶段。
3. **确定性验证** — 每项任务说明验收结果和验证方式；成功证据仍有效时复用，变更后检查受影响部分。
4. **集中交互** — 批量澄清；复审问题集中由用户裁决；人工验收集中确认，不重复索取已有决定。
5. **状态在盘上** — plan 记录任务进度、验证、复审和裁决。恢复时核对当前代码，从待办阶段继续。
6. **一套收尾规则** — [references/completion.md](references/completion.md) 定义验证、暂停和归档，多个入口共同引用。

## Commands

| 命令 | 使用场景 | 结束状态 |
|---|---|---|
| `/leanflow:plan` | 新功能、较大重构或重新设计 | 方案和验收标准落盘，等待执行 |
| `/leanflow:execute` | 按 plan 实施或中断后续跑 | 验证与复审处理完成、人工验收确认后自动归档；否则记录具体待办 |
| `/leanflow:review` | 单独审代码，或 execute 内部独立复审 | 集中呈现问题，按裁决修复并定向验证；独立调用不归档 |
| `/leanflow:debug` | 原因未知的报错、回归或异常 | 根因、修复和验证结果；也供 execute 内部使用 |
| `/leanflow:verify` | 兼容入口，或单独核对验证证据 | 报告通过、失败、未验证、待人工确认；不代替复审或自动归档 |
| `/leanflow:finish` | 兼容入口，或手动控制计划收尾 | 补足必要检查，条件满足后归档；Git 收尾按明确指令处理 |

`verify` 与 `finish` 继续可用，但日常无需逐个调用。
单独 review 不要求 plan，可审当前工作区或用户指定的提交范围。

## Typical workflow

```text
/leanflow:plan 加用户积分系统
# 批量澄清，生成 plans/add-user-points.md，确认方案

/leanflow:execute plans/add-user-points.md
# 实施 → 任务与全局验证 → 一次独立复审
# 有 findings：集中等待用户裁决，修复后定向验证与复核
# 有人工验收：保留待验收状态，确认后自动归档到 plans/done/
```

- 执行以主会话内联为主，连续独立的自动任务打包给一个 implementer；独立性同时考虑文件、接口、数据与状态。
- implementer 与主会话共享工作区，隔离的是 context。implementer 不提交、不勾选、不归档。
- 主会话保留逐任务提交规则；只暂存对应任务的改动，用户另有要求时遵从。
- 执行时验证失败，直接使用 debug 方法定位，修复后继续原流程。
- 复审结果和裁决写入 plan；续跑不重复完整复审或已经确认的事项。
- 未确认的人工验收不阻止无依赖的实现和复审，但会阻止归档。
- 已通过的证据不能覆盖后来变化的代码；只补进度记录或移动归档路径无需重跑业务测试。
- 自动归档不附带 squash、push、PR、merge 或删除分支；归档产生的计划文件改动会如实报告。

## Install

```bash
claude plugin marketplace add wennroy/leanflow
claude plugin install leanflow@leanflow
```

也可在 Claude Code 内通过 `/plugin` 交互界面完成。

## Hooks

**Stop 提醒（可选）**：项目根存在 `.claude/verify.sh` 时，每轮结束执行它。
适合简短的辅助检查；完整验收由 execute / review 的共用规则负责。
未创建该文件即不启用，可避免额外的每轮检查。

成功静默；失败最多保留末 100 行，使用 `systemMessage` 提醒，同样的失败只提醒一次。
它不会因失败强迫模型继续执行；退出码 0 和静默均不代表项目验证通过。
有 Python 3 时输出 JSON 提醒，缺少 Python 3 时退化为 stderr 诊断。
有 `timeout` / `gtimeout` 时设 180 秒上限，否则验证脚本须自行控制运行时间。

**PreToolUse 护栏**：保留对灾难性操作的尽力拦截，包括强删根/家/当前目录、
force push 到 main/master、清除整个工作区和磁盘破坏命令。放行时静默。
该脚本不是完整的 shell 安全边界。

## Maintenance

修改阶段行为时先更新对应 command；共用验证与归档规则只改
[references/completion.md](references/completion.md)，agent 职责放在 `agents/`。
不将整个流程塞进 router，也不为不同入口复制方法论。

```bash
claude plugin validate .
claude plugin validate .claude-plugin/plugin.json
claude plugin validate commands
claude plugin validate agents
claude plugin validate skills
python3 -m unittest discover -s tests -v
bash -n hooks/scripts/verify-on-stop.sh hooks/scripts/guard-dangerous.sh
git diff --check
```

测试覆盖 Stop 提醒的退出行为与去重；命令方法论还需用实际任务检查暂停、续跑、
无 plan 复审及人工验收边界，不能用匹配几句文案的测试代替行为验证。

## License

MIT
