#!/bin/sh
# 装上钩子：设置全局 core.hooksPath 指向本仓库的 hooks/ 目录。
# 重复执行是安全的。

set -e

DIR=$(cd "$(dirname "$0")" && pwd)
HOOKS="$DIR/hooks"
ENV="$HOOKS/commit-msg.env"

chmod +x "$HOOKS/prepare-commit-msg" "$HOOKS/gen-commit-msg.py"

if [ ! -f "$ENV" ]; then
    cp "$HOOKS/commit-msg.env.example" "$ENV"
    echo "已生成 $ENV —— 记得填 API_KEY"
fi
chmod 600 "$ENV"

OLD=$(git config --global --get core.hooksPath || true)
if [ -n "$OLD" ] && [ "$OLD" != "$HOOKS" ]; then
    echo "注意：原来的 core.hooksPath 是 ${OLD}，将被替换"
fi
git config --global core.hooksPath "$HOOKS"

echo "已启用：core.hooksPath = $(git config --global --get core.hooksPath)"
python3 -c 'import sys; print("python3 就绪:", sys.version.split()[0])'
