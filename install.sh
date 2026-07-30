#!/bin/sh
# 装上钩子：设置全局 core.hooksPath 指向本仓库的 hooks/ 目录。
# 卸载：./install.sh --uninstall  （还原 git 默认行为）
# 重复执行是安全的。

set -e

DIR=$(cd "$(dirname "$0")" && pwd)
HOOKS="$DIR/hooks"
ENV="$HOOKS/commit-msg.env"

case "$1" in
    --uninstall | -u)
        CUR=$(git config --global --get core.hooksPath || true)
        if [ "$CUR" = "$HOOKS" ]; then
            git config --global --unset core.hooksPath
            echo "已卸载：core.hooksPath 已取消，git 回到默认的 <仓库>/.git/hooks"
        elif [ -n "$CUR" ]; then
            echo "当前 core.hooksPath 是 ${CUR}，不是本仓库，未做改动"
        else
            echo "core.hooksPath 本来就没设置，无需卸载"
        fi
        [ -f "$ENV" ] && echo "配置文件仍保留（含 key）：$ENV"
        echo "要彻底删干净：rm -rf \"$DIR\""
        exit 0
        ;;
    "") ;;
    *)
        echo "用法：$0 [--uninstall]"
        exit 1
        ;;
esac

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
