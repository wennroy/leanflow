# leanflow

A lean, explicit-invocation workflow plugin for Claude Code.

**按需选择投入，围绕一份本地任务记录完成开发、验证与验收。**
常用入口仍是 `plan` 和 `execute`；小需求可以直接 execute，无需先单独规划。

## 使用

```text
/leanflow:execute --level low 修复表单必填校验
/leanflow:plan --level high 给订单页增加导出功能
/leanflow:execute
/leanflow:execute --level max 开发支持导入和筛选的账单工具
```

也可说「用 leanflow 的 high 档处理这个需求」「这个任务升级到 xhigh」。
`plan` 在任何档位都只出方案；`execute` 接受新需求、任务 id 或本地记录绝对路径。
无参数续跑当前明确的任务；多个候选才询问，不自动重开已完成任务。

## 五个 level

| 档位 | 开发方式 | Review 派发上限 | 验收 |
|---|---|---:|---|
| low | 全部内联，短计划，零子 Agent | 0 | 低成本相关检查 + UAT；不跑 Playwright |
| medium（默认） | 按 plan 的任务和用户指示委派或内联 | 2 | 无浏览器的相关单测/DOM/集成 + UAT |
| high | 按任务委派 | 3 | 独立 tester，核心旅程 E2E |
| xhigh | 按任务委派，范围内问题尽量收敛 | 6 | 约定场景、异常与相关回归 |
| max | 产品补场景、SubAgent 开发、整体验收 | 8 | 同 xhigh，加完整产品目标核对 |

medium 起支持「plan → subtask → subagent」，开发次数随任务安排，不设默认总派发硬上限。
例如 8 个适合独立委派的任务可以派发 8 次开发，再集中 Review 最多 2 次，仍然是 medium。
开发默认最多同时运行 2 个 Agent，受依赖和文件冲突约束；相关小任务可合并，不逐个微小步骤派发。
Review 围绕集成后的可验收批次，不默认给每个子任务附加一轮；高风险任务提前审查也计入同一额度。

Review 上限按整个需求累计，含修后复核，开发不会占用它。这些数值是初始策略，尚未完成
同任务下的速度/token 标定。总派发次数仍统计；用户可选设总上限，此时所有角色都占用总额度。
连续两轮无实质进展或同一故障连续三次修复失败就暂停该循环；不能拆任务或换 Agent 清除失败历史。
预算耗尽保留待办，不代表验证通过。任务恢复或换档不清零，显式预算调整须有用户授权。

优先级：本次明确选择 > 当前任务配置 > 项目默认 > medium。
档位控制工作流，不自动改模型 reasoning effort；不静默升档。
高档位也只加载当前需要的角色；非浏览器项目使用 API/CLI/集成旅程，Playwright 标不适用。
medium 默认不启动浏览器，现成脚本也一样；用户明确要求的特定浏览器检查可内联运行并记录，
不自动升档或派 tester。未覆盖的原故障路径留明确 UAT，不把无关单测全绿当作修复证据。

max 的产品 Agent 可补全既定目标内的遗漏场景，新增产品方向仍由用户决定。
范围内明确 bug 自动修，产品取舍集中问；独立 review 默认报告，已有修复授权时才改代码。
max 第一版在当前会话连续推进，中断可恢复；不提供跨会话后台调度。

## 本地 Memory

Git 项目存于 `git rev-parse --git-common-dir` 对应目录下的 `leanflow/`：

```text
leanflow/
  project.md          # 可选：项目默认档位与稳定决定
  tasks/<需求名>.md   # 每个需求唯一记录：计划、进度、问题、验证、UAT、下一步
```

这是本地 Git 管理目录内的存储，不是工作区中的 tracked 文件。多个 worktree 可读同一份
记录，但代码不自动转移；恢复先核对来源工作区与证据，不能在新 worktree 重做一遍。
非 Git 项目回退到项目根 `.leanflow/`；之后初始化 Git 时，在暂存代码前运行
`/leanflow:memory migrate` 原样迁入 Git 管理目录，保留任务、默认值与累计预算。
存在目标冲突时拒绝覆盖；未迁移前提示处理，不会当作新任务重建。

子任务和子 Agent 不另建 .sdd/plan/handoff。记录按批次或关键决定更新，恢复只读相关内容；
done 在原文件标记完成，不生成第二份归档。原始日志/trace 按需保留，引用路径即可。

```text
/leanflow:memory list
/leanflow:memory show login
/leanflow:memory default low
/leanflow:memory export login --to docs/leanflow/login.md
```

export 生成精选、带来源的 Markdown 快照，保留本地记录，不自动暂存或提交。
已有 `plans/*.md` 可显式迁移，保留原文件；必须带入原来的调用次数与真实基线，不能重置。
详见 [Memory 入口](commands/memory.md) 与 [状态规则](references/memory.md)。

## 命令与完成条件

| 命令 | 用途 |
|---|---|
| `/leanflow:plan` | 需求到可执行方案，保存 level，不自动实施 |
| `/leanflow:execute` | 新需求或续跑；开发、分档验证/Review、UAT、交付 |
| `/leanflow:review` | 指定任务或 diff 的独立审查，支持无 plan |
| `/leanflow:debug` | 复现、定位、修复与相关回归 |
| `/leanflow:verify` | 只核对证据和缺口，兼容旧用法 |
| `/leanflow:finish` | 沿用档位与预算补收尾，兼容旧用法 |
| `/leanflow:memory` | 查看任务、设置默认、导出文档 |

自动验证结束可以交付 UAT；用户沉默不能算验收通过。失败、未验证、不适用和已通过明确区分。
交付 checkpoint 同时保存四项摘要（相关验证、Review、E2E、UAT）并返回 delivery 缺口。
缺少必需 Review 或失败仍未处置时不能宣称自动验收完成；UAT 确认也不覆盖这些缺口。
工具拒绝不满足记录中完成条件的 done；明确豁免须附用户决定，不能写成通过。
摘要仍保存在原 Markdown，low 普通交付仍可只写初始化/交付两次。旧记录可读，首次交付
更新时依据已有证据补齐摘要即可，不因格式升级重跑整套验证。
验证绑定相关代码（含未提交变化）、依赖与环境，仍有效就复用，变化后只补受影响部分。
代码按完整改动批次提交，保留用户已有改动；push/PR/部署/merge 等沿用明确授权。
发布需要时准备构建、迁移/回滚、发布后检查和观察点，验证与交付规则集中在
[completion.md](references/completion.md)。

## 安装与运行依赖

```bash
claude plugin marketplace add wennroy/leanflow
claude plugin install leanflow@leanflow
```

本地 worktree 安装先把该目录登记为 marketplace，再按插件名安装，不能把裸路径当插件名：

```bash
claude plugin marketplace add /absolute/path/to/leanflow
claude plugin install leanflow@leanflow
claude plugin list
```

核对实际来源目录及 manifest 版本（本版 0.3.3）；同名 marketplace 已存在时先检查指向，
按宿主的更新/重新登记方式处理冲突，避免仍加载另一目录的旧版。已开启会话需按宿主机制
重载插件或开始新会话。以上是 Claude Code 入口；其他宿主使用自己的安装机制。

状态工具使用 Python 3.9+ 标准库，支持 macOS/Linux（目录锁依赖 `fcntl`）。无需数据库、
常驻服务或新增 Python 包。Claude Code 原生插件结构保持不变；其他宿主若迁移这些指令，
需提供插件文件路径与等价 Agent 工具，不宣称已完成所有宿主的集成验证。
入口从宿主提供的实际安装路径或入口文件位置定位，不依赖 shell 中存在 CLAUDE_PLUGIN_ROOT。
0.3.0 验收已有 Claude Code Skill 和 Codex 已安装 router 的实际调用证据；DSH 当时只有
授权模拟路径，没有原生加载证据。本次 0.3.3 未重新执行完整跨宿主行为验收。

辅助工具可单独运行：

```bash
python3 scripts/leanflow.py --help
python3 scripts/leanflow.py --cwd /path/to/project locate
```

Slash command 的参数由 Agent 按命令指令解析；状态工具负责确定性地保存和核对预算，
不拦截插件之外的宿主调用。它会在派发前原子预留额度，checkpoint 用 revision 拒绝旧状态覆盖。
总上限未设置时 `policy.agent_limit` 为 `null`，reserve 仍累计派发次数并检查 Review 上限。
旧任务无需迁移；已有显式总上限继续生效，可按用户要求通过 `budget --agents unlimited`
撤销，累计次数和 Review 上限保持。并发与任务分配由主协调者执行，状态工具不运行或调度 Agent。
交付摘要会检查所选档位的必需项及基本计数一致性；脚本不能判断证据真假、一次 Review
是否有价值或 UAT 是否真实通过，也不能自动感知所有代码/环境变化，协调者须核对证据。

## Hooks

不添加 SessionStart 注入或逐工具记账 hook。保留已有两项：

- Stop：只有项目存在 `.claude/verify.sh` 才执行；成功静默，相同失败提醒去重。
  它是项目自选检查，可能包含重型命令，不受 level 控制；追求轻量时应保持短小或不配置。
  hook 静默/退出 0 不代替任务验收证据。有 timeout/gtimeout 时限制 180 秒，否则脚本自行限时。
- PreToolUse：尽力拦截灾难性删除、对 main/master 的 force push 等操作；不是完整 shell 安全边界。

## 验证与维护

```bash
python3 -m unittest discover -s tests -v
bash -n hooks/scripts/verify-on-stop.sh hooks/scripts/guard-dangerous.sh
python3 scripts/check_package.py
git diff --check
```

已安装 Claude CLI 时再执行 `claude plugin validate .` 验证原生打包。
状态工具测试在临时 Git 仓库与 linked worktree 中验证实际行为，包括预算竞争、恢复、
未提交代码指纹和显式导出；它们不证明 Agent 遵循所有流程。
[行为验收场景](tests/behavioral.md) 用于独立实际执行，覆盖 low、预算、恢复、E2E 与 max。
本地安装后可将[完整验收 Prompt](tests/acceptance-prompt.md) 交给新 agent，使用真实插件入口执行。
速度统计以同任务、同验收、同模型/环境的测量为准；没有数据就不宣称提速百分比。
任务成功写入数从 new 的 revision=0 起算为 revision+1（截取阶段时用差值）；default 和导出
单列，level/budget/reserve 也计更新。耗时区分实际工作、宿主中断/等待与采集尾部延迟，
并记录同时启用的其他技能，不把它们混成 leanflow 的纯流程开销。

修改共用策略更新 references；角色职责放 agents；不要把全套方法论塞进 router，
也不要为不同 level 复制五套命令或为每个子任务创建记忆文件。
命令 frontmatter 的 `argument-hint` 统一使用 JSON 双引号字符串，避免参数中的方括号被
YAML 解析为数组；离线结构检查会校验这项约定，但不是完整的 YAML 解析器。

## License

MIT
