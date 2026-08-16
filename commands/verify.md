---
description: 收尾终检清单：全局验收、调试残留扫描、非目标核对、plan 完整性
argument-hint: [plan 文件路径]
---

# /leanflow:verify

feature 收尾前的清单式终检。execute 跑过的全局验收这里再确认一次
（review 阶段可能改过代码），外加 execute 不管的软性检查。

## 清单（逐项过，逐项报 ✅/❌）

1. **plan 完整**：plan 里所有任务已勾选；有 `[人工]` 项的，
   确认用户已验收。
2. **全局验收**：跑 plan 的「全局验收」命令，必须通过。
3. **调试残留**：在 diff 里搜 `console.log` / `debugger` /
   `TODO` / `FIXME` / 大段被注释的代码——找到就列出，
   问用户留还是删。
4. **非目标核对**：diff 里不该出现「非目标」节列的东西；
   出现了就是 scope 蔓延，报给用户。
5. **关键决定对照**：diff 与「关键决定」逐条对照，违反的报出
   （review 之后没新改动可跳过）。

## 结果

- 全 ✅ → 「终检通过，可以 /leanflow:finish。」
- 有 ❌ → 列出清单，问用户：修 / 豁免 / 加任务回 plan。
