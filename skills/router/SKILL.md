---
name: leanflow-router
description: 用户明确使用 leanflow 或其 effort level 时路由到对应命令；普通多步骤开发仅建议一次。普通小修、提问和探索不自动启动流程。
---

# Leanflow Router

用户明确说「用 leanflow high/low/max 档」「继续 leanflow 任务」或使用命令时：

- 只要方案/讨论 → 读取插件根 `commands/plan.md`。
- 要实施/续跑 → 读取 `commands/execute.md`。
- 明确只审查、调试、验证或收尾 → 对应 review/debug/verify/finish 命令。
- 设置项目默认、查看记忆、导出 docs → `commands/memory.md`。
- 自然语言明确指定的 level 等价于 `--level`，支持 low/medium/high/xhigh/max（忽略大小写）。
  升降档跟随当前任务保存，不把模型 reasoning effort 自动映射成流程档位。

插件根从宿主给出的实际安装目录或本文件祖先目录定位，核实 `.claude-plugin/plugin.json`
的 name=leanflow 与 `scripts/leanflow.py`；当前源码布局为本文件目录向上两级。
`CLAUDE_PLUGIN_ROOT` 仅作候选，不假定 shell 中存在。将核实后的绝对路径交给对应命令，
同会话复用；只读当前入口，后续按需加载。缺入口时报告安装限制，不拿别处源码冒充已安装。

用户未明确使用 leanflow 时，仅对多步骤、多文件的开发/重构建议一次：
「这个需求可以用 leanflow，默认 medium；也可以直接开始。」随后继续正常工作。
不采纳就不重复提醒，不强制先 plan；普通小修、提问、探索保持静默。
「高优先级」「简单」不等价于选档，普通任务不会因此进入 leanflow。
