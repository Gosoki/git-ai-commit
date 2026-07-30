# git-ai-commit

> 提交时自动生成中文 + emoji 的 Conventional Commits 消息。用你自己的 API，一个 git 钩子搞定，不装扩展。

```
✨feat(auth): 新增短信验证码登录功能

📝docs(readme): 添加认证模块说明
🐛fix(session): 修复 token 过期后未清理缓存
🧪test(auth): 增加登录失败的测试用例
🔨build(requirements): 更新依赖库版本
```

---

## 为什么有这个

VSCode 内置的「生成提交消息」按钮有两个死结：

1. 只要 `github.copilot.chat.commitMessageGeneration.instructions` 非空，请求必定 422 失败
   （[vscode#315997](https://github.com/microsoft/vscode/issues/315997) 的回归，`text` 和 `file` 两种写法都中招）——
   也就是**能用的时候管不了格式，想管格式就不能用**。
2. 模型写死 `gpt-4o-mini`，没有任何配置项，BYOK 也不作用于这个按钮。

这个钩子绕开整条链路：格式你自己定，模型你自己选，key 你自己的。

## 特性

- **中文 + emoji + Conventional Commits**，规则可改
- **多文件出「主题行 + 明细」**，单文件只出一行，不硬凑
- **多接口顺序故障转移**，主用挂了自动换备用
- **一个总开关**停用，`--uninstall` 一键还原
- **绝不阻塞提交**：网络不通、超时、key 失效一律静默跳过
- **零第三方依赖**：只用 Python 标准库，不装任何 pip 包
- macOS / Linux / Windows 通用

## 安装

```bash
git clone https://github.com/Gosoki/git-ai-commit.git ~/git-ai-commit
cd ~/git-ai-commit
./install.sh                    # 设置全局 core.hooksPath，所有仓库生效
vi hooks/commit-msg.env         # 填 key
```

`install.sh` 会自动：加执行权限 → 从模板生成配置文件 → 权限设为 600 → 写入全局
`core.hooksPath` → 检查 Python。重复执行安全；原来有别的 hooksPath 会先提示。

卸载：

```bash
./install.sh --uninstall        # 取消 core.hooksPath，git 回到默认行为
rm -rf ~/git-ai-commit          # 想连文件一起删就再来这句
```

只在 `core.hooksPath` 确实指向本仓库时才取消，指向别处会提示并保持不动。
配置文件不会被自动删除（里面有 key）。

## 配置

`hooks/commit-msg.env`，标准 INI。已被 `.gitignore` 忽略，**不会进版本库**。

```ini
[global]
enabled = true                      # 总开关，false 即停用
model = gpt-4o-mini                 # 各接口没单独写 model 时的默认值

[openai]
base = https://api.openai.com/v1    # 填到 /v1 为止，脚本自动拼 /chat/completions
key = sk-xxxxxxxx
model = gpt-4o-mini                 # 可省略，省略则用 [global] 的

[中转]
base = https://xxx.example.com/v1
key = sk-yyyyyyyy
model =
```

| 位置 | 键 | 说明 |
|---|---|---|
| `[global]` | `enabled` | 总开关，`false`/`no`/`off`/`0` 均可，不填视为开启 |
| `[global]` | `model` | 默认模型 |
| 接口段落 | `base` | 接口地址，OpenAI 兼容格式 |
| 接口段落 | `key` | API key |
| 接口段落 | `model` | 该接口的模型，留空则回退到 `[global]` |

值带引号、行尾带 `#` 注释都能正确解析。模型取值顺序：段落 `model` → `[global] model` → `gpt-4o-mini`。

### 多接口故障转移

`[global]` 之外**每个段落就是一个接口**，段落名随便起（只用于调试日志）。
**按文件里从上到下的顺序试**，前一个失败自动换下一个，第一个成功就返回：

- 触发换下一个：超时（30 秒）、401、限流、服务端报错、返回空内容
- 没填 `key` 的段落直接跳过，所以备用接口可以先留空占位
- 想调优先级，上下挪段落即可

## 用法

**VSCode / code-server**

> 提交消息框**留空** → 点 ✓ → 弹出 `COMMIT_EDITMSG` 标签页，消息已生成好

| 想干什么 | 怎么做 |
|---|---|
| 直接提交 | `Cmd+W` 关掉标签页，或点内容区浮出的 **Commit** |
| 改一改再提交 | 在标签页里编辑，改完 `Cmd+W` |
| 取消这次提交 | 点内容区浮出的 **Cancel**；或把内容**全部删光**再关（更保险） |

注意标签页右上角的关闭 `×` 是**提交**，不是取消。想取消认准 Cancel 按钮或清空内容。

**终端**

```bash
git commit          # 不要带 -m
```

## 不想让它生成

| 场景 | 做法 |
|---|---|
| 这一次 | `git commit -m "自己写的"`，或 `NO_AI_COMMIT=1 git commit` |
| 停用一段时间 | 配置里 `enabled = false`，想用了改回 `true` |
| 某个仓库 | 在该仓库里 `git config core.hooksPath .git/hooks` |
| 彻底卸载 | `./install.sh --uninstall` |

钩子在这些情况下也会自动让路：已用 `-m` 给了消息、merge / squash / 模板 / amend、暂存区为空。

## 排查

```bash
AI_COMMIT_DEBUG=1 git commit
```

会打印实际用了哪个接口、失败原因和响应体前 300 字：

```
[没填key的] 缺 base 或 key，跳过
[主用] 失败: <HTTPError 429: 'Too Many Requests'> {"error":{"message":"insufficient_quota"}}
使用 [中转] (https://xxx.example.com/v1, gpt-4o-mini)
```

不加这个环境变量时，任何失败都是静默的——**宁可不生成，也不阻塞你提交**。

## 工作原理

```
git commit
   └─ git 调用 core.hooksPath 下的 prepare-commit-msg
        ├─ 判断该不该介入（-m / merge / 停用 / 空暂存区 → 直接放行）
        ├─ 取 staged diff（上限 100 KB）
        ├─ 管道喂给 gen-commit-msg.py
        │    └─ 读 commit-msg.env，按段落顺序请求，取第一个成功的
        └─ 把消息写进提交消息文件的开头
   └─ 编辑器打开，你看到已填好的消息
```

提交消息的风格规则写在 `hooks/gen-commit-msg.py` 的 `RULES` 变量里，改完下次提交立即生效。

## 文件结构

```
git-ai-commit/
├── install.sh                     安装 / 卸载
├── hooks/
│   ├── prepare-commit-msg         钩子本体
│   ├── gen-commit-msg.py          调接口的实现，规则在 RULES 里
│   ├── commit-msg.env.example     配置模板（进版本库）
│   └── commit-msg.env             你的配置，含 key（被忽略，600 权限）
├── .gitattributes                 强制脚本以 LF 检出
└── .gitignore
```

## 平台说明

依赖只有 `git`、Python 3、`sh`。

**Windows**：在 Git Bash 里执行安装命令，日常在 VSCode 里点提交不用开终端。两个坑已处理：

- Windows 上一般没有 `python3` 这个名字，钩子会依次探测 `python3` → `python` → `py -3`
- `.gitattributes` 强制脚本以 LF 检出，否则 `core.autocrlf` 会让 Git Bash 报
  `$'\r': command not found` 并静默失效

**服务器 / code-server**：钩子在「git 实际执行的那台机器」上跑，所以要装在服务器：

```bash
ssh HOST 'git clone https://github.com/Gosoki/git-ai-commit.git ~/git-ai-commit && cd ~/git-ai-commit && ./install.sh'
ssh HOST 'vi ~/git-ai-commit/hooks/commit-msg.env'
```

- key 会留在那台机器上，公用机器建议单独申请一个
- 国内服务器直连 `api.openai.com` 不通，配个中转地址，或给 git 进程带上
  `https_proxy` 环境变量（脚本用的 urllib 会自动读）
