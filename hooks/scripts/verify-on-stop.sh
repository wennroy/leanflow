#!/usr/bin/env bash
# leanflow · Stop hook
# 项目根存在 .claude/verify.sh 时，每轮结束跑一次验证：
#   成功 → 静默放行（零输出，零 token）
#   失败 → 截断输出喂给模型（exit 2）；同样的失败不重复阻断（防 nag 循环）
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

# 同样的失败已报过一次 → 放行，不 nag
if [ -f "$STATE_FILE" ] && [ "$(cat "$STATE_FILE")" = "$hash" ]; then
  exit 0
fi
printf '%s' "$hash" > "$STATE_FILE"

printf '项目验证（.claude/verify.sh）失败，请修复后再收尾：\n%s\n' "$trimmed" >&2
exit 2
