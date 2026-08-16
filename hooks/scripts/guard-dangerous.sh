#!/usr/bin/env bash
# leanflow · PreToolUse hook（matcher: Bash）
# 危险命令护栏：只拦灾难性操作，不做风格警察。
# 拦截时 stderr 一句话 + exit 2；放行零输出。
set -uo pipefail

input=$(cat)

# 提取 tool_input.command（优先 python3，退化到 grep）
cmd=""
if command -v python3 >/dev/null 2>&1; then
  cmd=$(printf '%s' "$input" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("tool_input",{}).get("command","") or "")' 2>/dev/null || true)
fi
if [ -z "${cmd}" ]; then
  cmd=$(printf '%s' "$input" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/^[^:]*:[[:space:]]*"//; s/"$//')
fi
[ -z "${cmd}" ] && exit 0

block() {
  printf '🚫 leanflow 拦截：%s\n命令：%.200s\n如确认需要，请用户手动执行。\n' "$1" "$cmd" >&2
  exit 2
}

# 去掉引号便于匹配（护栏是 best-effort，不是安全边界）
norm=$(printf '%s' "$cmd" | tr -d "\"'")

# 1. 递归强删根目录 / 家目录 / 当前目录
#    目标必须是这些路径本身（后跟分隔符或结尾），不误伤 rm -rf /tmp/xxx、~/.cache、./build
printf '%s' "$norm" | grep -Eq 'rm[[:space:]]+(-[a-zA-Z]+[[:space:]]+)*-[a-zA-Z]*[rf][a-zA-Z]*[[:space:]]+(/|/\*|~|~/|\$HOME|\$HOME/|\.|\./)([[:space:];&|]|$)' \
  && block 'rm 递归强删根目录/家目录/当前目录'

# 2. force push 到 main/master
printf '%s' "$norm" | grep -Eq 'git[[:space:]]+push\b.*(-f\b|--force\b|--force-with-lease\b).*\b(main|master)\b' \
  && block 'force push 到 main/master'

# 3. 销毁未提交改动
printf '%s' "$norm" | grep -Eq 'git[[:space:]]+clean[[:space:]]+-[a-zA-Z]*f' \
  && block 'git clean -f 会删除未跟踪文件'
printf '%s' "$norm" | grep -Eq 'git[[:space:]]+(checkout|restore)[[:space:]]+(--[[:space:]]+)?\.([[:space:]]|$)' \
  && block '丢弃整个工作区的未提交改动'

# 4. 磁盘/系统级破坏
printf '%s' "$norm" | grep -Eq '\bmkfs\b|\bdd\b.*\bof=/dev/|: *\(\) *\{' \
  && block '磁盘/系统级破坏操作'

exit 0
