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

| 档位 | 开发方式 | Review 上限 | 全部 Agent 上限 | 验收 |
|---|---|---:|---:|---|
| low | 全部内联，短计划 | 0 | 0 | 低成本相关检查 + UAT；不跑 Playwright |
| medium（默认） | 内联为主 | 2 | 2 | 相关单测/集成 + UAT |
| high | 必要时打包委派 | 3 | 6 | 独立 tester，核心旅程 E2E |
| xhigh | 范围内问题尽量收敛 | 6 | 12 | 约定场景、异常与相关回归 |
| max | 产品补场景、SubAgent 开发、整体验收 | 8 | 24 | 同 xhigh，加完整产品目标核对 |

这些数值是初始策略，尚未完成同任务下的速度/token 标定。上限包含规划期与修后复核；
Review 同时消耗总额度。连续两轮无实质进展或同一故障连续三次修复失败就暂停该循环。
预算耗尽保留待办，不代表验证通过。任务恢复或换档不清零，用户可明确追加累计上限。

优先级：本次明确选择 > 当前任务配置 > 项目默认 > medium。
档位控制工作流，不自动改模型 reasoning effort；不静默升档。
高档位也只加载当前需要的角色；非浏览器项目使用 API/CLI/集成旅程，Playwright 标不适用。

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
验证绑定相关代码（含未提交变化）、依赖与环境，仍有效就复用，变化后只补受影响部分。
代码按完整改动批次提交，保留用户已有改动；push/PR/部署/merge 等沿用明确授权。
发布需要时准备构建、迁移/回滚、发布后检查和观察点，验证与交付规则集中在
[completion.md](references/completion.md)。

## 安装与运行依赖

```bash
claude plugin marketplace add wennroy/leanflow
claude plugin install leanflow@leanflow
```

状态工具使用 Python 3.9+ 标准库，支持 macOS/Linux（目录锁依赖 `fcntl`）。无需数据库、
常驻服务或新增 Python 包。Claude Code 原生插件结构保持不变；其他宿主若迁移这些指令，
需提供插件文件路径与等价 Agent 工具，不宣称已完成所有宿主的集成验证。

辅助工具可单独运行：

```bash
python3 scripts/leanflow.py --help
python3 scripts/leanflow.py --cwd /path/to/project locate
```

Slash command 的参数由 Agent 按命令指令解析；状态工具负责确定性地保存和核对预算，
不拦截插件之外的宿主调用。它会在派发前原子预留额度，checkpoint 用 revision 拒绝旧状态覆盖。
脚本不能判断一次 Review 是否有价值、UAT 是否真实通过；这些仍需要执行证据。

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

修改共用策略更新 references；角色职责放 agents；不要把全套方法论塞进 router，
也不要为不同 level 复制五套命令或为每个子任务创建记忆文件。

## License

MIT
