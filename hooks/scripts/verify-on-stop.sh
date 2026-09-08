#!/usr/bin/env bash
# leanflow · 可选 Stop 提醒，不负责 feature 验收
# 项目根存在 .claude/verify.sh 时，每轮结束探测一次：
#   成功 → 静默
#   失败 → 提醒但不阻止当前轮次结束；同样的失败不重复提醒
# 所有正常路径 exit 0 仅表示 hook 不阻断，不表示项目验证通过。
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
VERIFY="$ROOT/.claude/verify.sh"
[ -f "$VERIFY" ] || exit 0

# 跑验证（有 timeout/gtimeout 就加 180s 上限，没有就直接跑）
if command -v timeout >/dev/null 2>&1; then
  output=$(cd "$ROOT" && timeout 180 bash "$VERIFY" 2>&1)
elif command -v gtimeout >/dev/null 2>&1; then
  output=$(cd "$ROOT" && gtimeout 180 bash "$VERIFY" 2>&1)
else
  output=$(cd "$ROOT" && bash "$VERIFY" 2>&1)
fi
status=$?

STATE_DIR="${TMPDIR:-/tmp}/leanflow-verify"
mkdir -p "$STATE_DIR"
KEY=$(printf '%s' "$ROOT" | cksum | tr -d ' ')
STATE_FILE="$STATE_DIR/$KEY"

if [ "$status" -eq 0 ]; then
  rm -f "$STATE_FILE"
  exit 0
fi

# 失败：截断到末 100 行（防爆 context）
trimmed=$(printf '%s\n' "$output" | tail -100)
hash=$(printf '%s' "$trimmed" | cksum | tr -d ' ')

# 同样的失败已提醒过 → 静默，项目验证仍然失败
if [ -f "$STATE_FILE" ] && [ "$(cat "$STATE_FILE")" = "$hash" ]; then
  exit 0
fi
printf '%s' "$hash" > "$STATE_FILE"

message=$(printf 'leanflow 辅助检查（.claude/verify.sh）失败，退出码 %s。此提醒不阻止提问或暂停；任务完成仍需有效的验证与验收证据。\n%s\n' "$status" "$trimmed")
if command -v python3 >/dev/null 2>&1; then
  printf '%s' "$message" | python3 -c 'import json,sys; print(json.dumps({"systemMessage": sys.stdin.read()}, ensure_ascii=False))'
else
  # 无 JSON 编码器时退化为普通诊断，仍不能迫使模型继续修复。
  printf '%s\n' "$message" >&2
fi
exit 0
