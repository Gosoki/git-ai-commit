#!/usr/bin/env python3
"""读 stdin 的 git diff，调用 OpenAI 兼容接口生成提交消息，打印到 stdout。
配了多个接口时按顺序试，前一个失败就换下一个。
出任何问题都静默退出（打印空），由钩子决定不改提交消息。
配置见同目录 commit-msg.env，调试加 AI_COMMIT_DEBUG=1。"""

import json
import os
import re
import sys
import urllib.error
import urllib.request

CONF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "commit-msg.env")
TIMEOUT = 30

RULES = """根据用户给出的 git diff 写一条提交消息，只输出消息正文，不要解释、不要代码块包裹。

规则：
1. 全程简体中文，技术术语保留英文。
2. 每行格式 <emoji><type>(scope): 描述。
3. emoji 对照：feat✨ fix🐛 docs📝 style🎨 refactor♻️ perf⚡ test🧪 chore🧹 build🔨 ci🔧 revert⏪
4. 第一行是主题行，概括这次改动整体做了什么，type 和 emoji 取本次最主要的那个，50 字以内。
5. 改动涉及多个方面时，主题行后空一行，再逐条列明细：同一 type 只写一行，多个 scope 用逗号合并，
   如 ✨feat(auth,api,db): 描述；不同 type 各占一行。改动单一时只写主题行，不要硬凑明细。
6. 描述每行 50 字以内，说清改了什么，不写「修复bug」这类模糊表述。

多文件改动示例：
♻️refactor(auth): 重构登录链路并补齐测试

✨feat(auth,api): 新增短信验证码登录接口
🐛fix(session): 修复 token 过期后未清理缓存
🧪test(auth): 补充登录失败分支用例"""


def log(*a):
    if os.environ.get("AI_COMMIT_DEBUG"):
        print(*a, file=sys.stderr)


def load_conf():
    conf = {}
    with open(CONF, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = re.sub(r"\s+#.*$", "", v.strip())  # 容忍行尾注释
            conf[k.strip()] = v.strip().strip("'\"")  # 容忍引号
    return conf


def providers(conf):
    """按 API_BASE、API_BASE_2、API_BASE_3… 的顺序返回接口列表。"""
    found = set()
    for key in conf:
        m = re.match(r"API_BASE(_\d+)?$", key)
        if m:
            found.add(m.group(1) or "")

    out = []
    for sfx in sorted(found, key=lambda s: int(s[1:]) if s else 0):
        base, key = conf.get("API_BASE" + sfx), conf.get("API_KEY" + sfx)
        if not base or not key:
            continue
        out.append(
            {
                "name": "API_BASE" + sfx,
                "base": base.rstrip("/"),
                "key": key,
                "model": conf.get("API_MODEL" + sfx) or conf.get("API_MODEL", "gpt-4o-mini"),
            }
        )
    return out


def ask(p, diff):
    payload = {
        "model": p["model"],
        "messages": [
            {"role": "system", "content": RULES},
            {"role": "user", "content": diff},
        ],
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        p["base"] + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + p["key"],
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        body = json.load(resp)

    msg = body["choices"][0]["message"]["content"].strip()
    return "\n".join(l for l in msg.splitlines() if not l.startswith("```")).strip()


def main():
    diff = sys.stdin.read()
    if not diff.strip():
        return

    conf = load_conf()
    if conf.get("ENABLED", "true").lower() in ("false", "0", "no", "off"):
        log("ENABLED=false，已停用")
        return

    provs = providers(conf)
    if not provs:
        log("没有可用接口：至少要填一组 API_BASE + API_KEY")
        return

    for p in provs:
        try:
            msg = ask(p, diff)
            if msg:
                log("使用 %s (%s, %s)" % (p["name"], p["base"], p["model"]))
                print(msg)
                return
            log("%s 返回空内容，换下一个" % p["name"])
        except Exception as e:
            detail = ""
            if isinstance(e, urllib.error.HTTPError):
                detail = " " + e.read().decode(errors="replace")[:300]
            log("%s 失败: %r%s" % (p["name"], e, detail))

    log("所有接口都失败了")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("生成失败:", repr(e))
