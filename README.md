# git-ai-commit

用第三方 API（OpenAI 兼容接口）根据 staged diff 自动生成中文 + emoji 的提交消息。

起因：VSCode 内置的「生成提交消息」按钮在 `commitMessageGeneration.instructions`
非空时必定 422 失败（[vscode#315997](https://github.com/microsoft/vscode/issues/315997) 回归），
且模型写死 gpt-4o-mini、用不了自己的 key。这个钩子绕开整条链路。

## 效果

单文件改动只出主题行：

```
🎨style(config): 调整日志格式为 JSON
```

多文件改动出主题行 + 明细：

```
✨feat(auth): 新增短信验证码登录功能

📝docs(readme): 添加认证模块说明
🐛fix(session): 修复 token 过期后未清理缓存
🧪test(auth): 增加登录失败的测试用例
🔨build(requirements): 更新依赖库版本
```

## 安装

```bash
git clone <本仓库> ~/git-ai-commit
cd ~/git-ai-commit
./install.sh                    # 设置全局 core.hooksPath，所有仓库生效
vi hooks/commit-msg.env         # 填 API_KEY
```

卸载：

```bash
./install.sh --uninstall        # 取消 core.hooksPath，git 回到默认行为
rm -rf ~/git-ai-commit          # 想连文件一起删就再来这句
```

只依赖 `git`、`python3`（标准库，无需 pip 装任何东西）、`sh`。macOS 和 Linux 通用。

## 配置

`hooks/commit-msg.env`（已被 .gitignore 忽略，不会误传上去）：

| 键 | 说明 |
|---|---|
| `ENABLED` | 总开关，`false` 即停用自动生成（不填视为开启） |
| `API_BASE` | 接口地址，填到 `/v1` 为止，脚本自动拼 `/chat/completions` |
| `API_KEY` | 你的 key |
| `API_MODEL` | 模型名，按服务商支持的填 |

值带引号、行尾带注释都能正确解析。

### 多接口故障转移

加编号即可配多个，按数字从小到大依次尝试，前一个挂了（超时、401、限流、服务端报错、
返回空内容）自动换下一个，第一个成功就返回：

```ini
API_BASE=https://api.openai.com/v1
API_KEY=sk-主用
API_MODEL=gpt-4o-mini

API_BASE_2=https://中转.example.com/v1
API_KEY_2=sk-备用
API_MODEL_2=              # 不填就沿用上面的 API_MODEL

API_BASE_3=...
```

编号不必连续；只填了 `API_BASE_n` 没填对应 `API_KEY_n` 的会被跳过。
每个接口超时 30 秒。想知道实际用了哪个，跑 `AI_COMMIT_DEBUG=1 git commit`：

```
API_BASE 失败: <HTTPError 429: 'Too Many Requests'> {"error":{"message":"insufficient_quota"}}
使用 API_BASE_2 (https://中转.example.com/v1, gpt-4o-mini)
```

提交消息的风格规则写在 `hooks/gen-commit-msg.py` 的 `RULES` 变量里，想改格式改那儿，改完下次提交立即生效。

## 用法

- **VSCode / code-server**：提交消息框**留空**，直接点 ✓ → 弹出 COMMIT_EDITMSG 标签页，
  里面是生成好的消息 → `Cmd+W` 关掉即提交（想改就先改再关）。
  依赖 `git.useEditorAsCommitInput`，默认就是开的。
- **终端**：`git commit`，不要带 `-m`。

## 不想让它生成

| 场景 | 做法 |
|---|---|
| 这一次 | `git commit -m "自己写的"`，或 `NO_AI_COMMIT=1 git commit` |
| **停用一段时间** | **改 `hooks/commit-msg.env` 里的 `ENABLED=false`，想用了再改回 `true`** |
| 某个仓库 | 在该仓库里 `git config core.hooksPath .git/hooks` |
| **彻底卸载** | **`./install.sh --uninstall`**，还原 git 默认行为 |

停用状态下提交完全正常，只是不再自动写消息——消息框留空会因为空消息而中止提交，
自己写一条即可。

## 排查

```bash
AI_COMMIT_DEBUG=1 git commit
```

会打印 HTTP 错误和响应体前 500 字。默认情况下任何失败（网络不通、超时、key 无效）
都静默跳过，**不会阻塞提交**。

## 装到服务器

钩子在「git 实际执行的那台机器」上跑。用 code-server 或 Remote-SSH 时 git 跑在服务器上，
所以要装在服务器：

```bash
ssh HOST 'git clone <本仓库> ~/git-ai-commit && cd ~/git-ai-commit && ./install.sh'
ssh HOST 'vi ~/git-ai-commit/hooks/commit-msg.env'
```

两个注意：

- key 会留在那台机器上，公用机器建议单独申请一个 key。
- 国内服务器直连 `api.openai.com` 不通，改 `API_BASE` 为中转地址，
  或给 git 进程带上 `https_proxy` 环境变量（脚本用的 urllib 会自动读）。
