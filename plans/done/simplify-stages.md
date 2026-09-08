# 简化 leanflow 阶段
> 状态：已完成

## 目标

保留 Claude Code 插件组织，让 plan / execute 覆盖日常开发流程。
execute 自动完成验证和一次独立复审，集中等待用户裁决；人工验收完成后自动归档。
review / debug 支持独立使用，verify / finish 保留为复用共同规则的兼容入口。

## 非目标

- 不新增 Codex 入口或模型配置，不安装或发布插件。
- 不改变批量澄清、内联优先和整包派发的基本方式。
- 不自动提交、推送本次插件修改；被描述的 execute 仍保留逐任务提交规则。

## 关键决定

- 收尾规则维护在 `references/completion.md`，各命令按阶段引用。
- 复审问题集中交给用户裁决；已有裁决在续跑时继续有效。
- 待裁决、待人工验收、阻塞均不等于完成，不提前归档。
- 没有 plan 也可以 review；独立 review 不触发项目归档。
- Stop hook 只提供辅助提醒，不能阻止提问，也不能充当完成依据。

## 全局验收

- `python3 -m unittest discover -s tests -v`：验证 Stop hook 不阻止结束、失败提醒与去重、成功清理。
- `bash -n hooks/scripts/verify-on-stop.sh hooks/scripts/guard-dangerous.sh`。
- JSON 可解析、Markdown 本地引用存在、`git diff --check`。
- `claude plugin validate .`、`claude plugin validate .claude-plugin/plugin.json`，以及 commands / agents / skills 的组件校验。
- 独立场景推演：正常收尾、无计划复审、待人工验收、裁决后续跑、归档兼容入口。

## Tasks

- [x] T1 共用收尾规则与执行闭环 [顺序]
  - 改动：`references/completion.md`、`commands/execute.md`、`commands/plan.md`。
  - 要点：记录验证和复审对应的代码状态，按已完成阶段续跑；区分自动任务、待裁决与人工验收。
  - verify: 本地引用检查、正常收尾/暂停/续跑场景推演。
- [x] T2 独立入口与兼容入口 [顺序]
  - 改动：`commands/review.md`、`commands/verify.md`、`commands/finish.md`、`commands/debug.md`、`agents/implementer.md`、`agents/reviewer.md`。
  - 要点：复用收尾规则，无 plan 也可 review，内部调试不中断工作流；检查发现问题后有针对性复核。
  - verify: 无计划复审/人工任务派发/裁决后续跑场景推演。
- [x] T3 Stop hook 辅助提醒 [独立]
  - 改动：`hooks/scripts/verify-on-stop.sh`、`tests/test_verify_on_stop.py`。
  - 要点：先用失败测试证明当前 hook 阻断当前轮次，再使失败仅产生明确提示，保留去重。
  - verify: `python3 -m unittest discover -s tests -v`。
- [x] T4 文档与整体验证 [顺序]
  - 改动：`README.md`、`.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json`、本计划。
  - 要点：说明两个常用入口、独立工具与兼容入口，保持元信息一致；通过后归档计划。
  - verify: 全局验收与一次独立复审。

## 执行记录

- 起点：`c78a314`，初始工作区干净。
- 需求来源：本会话已确认的阶段划分与合并方向。
- 初步证据：旧 Stop hook 首次失败返回 2；execute 全局验收通过后要求用户另行调用 review。
- 基线场景推演确认：旧 execute 不自动复审与归档，无 plan review 路径未定义，待人工项阻止后续复审，续跑不恢复复审裁决阶段。
- 验证：5 项 hook 测试通过；旧 hook 在其中 2 项失败，新 hook 修正了阻断行为。Shell 语法、JSON、10 处本地引用与 Claude Code 原生插件/组件校验通过。
- 独立复审：发现旧 plan 缺基线时可能漏审已提交任务，已补回溯规则；定向复核通过，未发现新的阻塞项。
- 新版 6 个场景复核：自动进入复审、无 plan 可独立审、等待人工确认、按已有裁决续跑、finish 不提前归档、verify 不冒充完整收尾。
- 验证范围：脚本真实执行与方法论场景推演；尚未在真实业务项目的 Claude Code 会话中完整试跑。
- 交付：工作区改动与本计划归档，未提交、安装或发布插件。
