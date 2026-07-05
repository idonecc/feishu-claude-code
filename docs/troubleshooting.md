# 疑难排查手册

真实踩坑记录，每一条都在生产环境验证过。按报错信息直接对号入座。

## 快速索引

| 症状 | 跳转 |
|------|------|
| 回复 `Failed to authenticate. API Error: 403 Request not allowed` | [403 双根因](#403-request-not-allowed中国大陆用户最高频) |
| 回复 `Not logged in · Please run /login` | [登录态问题](#not-logged-in) |
| 发图片报 `403 Request not allowed`（飞书 API 层） | [缺少资源权限](#图片下载-403) |
| 服务反复重启，日志 `ModuleNotFoundError: lark_oapi` | [Python 环境](#modulenotfounderror-lark_oapi) |
| 启动报 `OSError: [Errno 48] Address already in use` | [端口占用](#address-already-in-use) |
| ngrok 启动失败 `ERR_NGROK_9009` | [ngrok 与代理冲突](#ngrok-err_ngrok_9009) |
| `/` 命令正常但普通提问失败 | [403 双根因](#403-request-not-allowed中国大陆用户最高频)（`/` 是本地处理，提问才走 Claude API） |

---

## 403 Request not allowed（中国大陆用户最高频）

**同一句报错，背后有两个完全独立的根因。** 修好一个另一个还在，极易误判成"没修好"。

### 根因 A：环境变量污染（继承了网关配置）

如果 bot 进程是从某个已配置 `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` 的终端（或 Claude Code 会话）里启动的，claude CLI 会**放弃订阅登录态**，改用这些变量指向的网关，被网关拒绝 → 403。

**本项目已内置修复**：`claude_runner.py` 在 spawn 子进程前剥离所有 `ANTHROPIC_*` / `CLAUDE_CODE*` / `CLAUDECODE` 变量，日志会打印：

```
[run_claude] 已剥离环境变量: ANTHROPIC_AUTH_TOKEN, ANTHROPIC_BASE_URL, ...
```

### 根因 B：大陆 IP 被 Anthropic 地区封锁

launchd/systemd 守护进程的环境是"干净"的——**没有你 shell 里的代理变量**。claude CLI 直连 `api.anthropic.com`，Anthropic 对大陆 IP 返回的正是 `403 Request not allowed`（与根因 A 报错一字不差！）。

**一条命令鉴别**：

```bash
# 不带代理直连
curl -s --noproxy '*' -o /dev/null -w "%{http_code}\n" \
  https://api.anthropic.com/v1/messages -X POST -d '{}'
# 返回 403 → 你的 IP 被地区封锁，是根因 B
# 返回 401 → 链路正常（只是没带 key），403 另有原因
```

**修复**：在 `.env` 配置出境代理，bot 会只给 claude 子进程注入（飞书 API 仍走国内直连）：

```ini
CLAUDE_PROXY=http://127.0.0.1:10808
```

日志确认注入生效：

```
[run_claude] 代理: http://127.0.0.1:10808
```

### 为什么日志里看不出错误？

claude CLI 把这类错误当作**正常 result 正文**返回（`is_error=True` 但流程"成功完成"），bot 会把错误文本原样发到飞书。本项目日志已记录 result 事件的关键字段：

```
[run_claude] result: is_error=True subtype=success duration_ms=1297 cost=$0.0000 text[:200]='Failed to authenticate...'
```

看到 `is_error=True` + `cost=$0.0000` + 秒级失败 → 请求根本没到模型，按上面两个根因排查。

---

## Not logged in

claude CLI 未登录或登录态不可用。

```bash
claude auth status   # 查看登录状态
claude auth login    # 重新登录（需要 Max/Pro 订阅）
```

注意：macOS 登录凭证存在 Keychain，`env -i` 之类的极端干净环境会拿不到登录态。launchd gui domain 正常可访问 Keychain，无需特殊处理。

---

## 图片下载 403

发送图片后 bot 回复飞书 API 层的 403。这是**飞书应用权限**问题，与 Claude 无关：

飞书开放平台 → 你的应用 → 权限管理 → 开启 `im:resource`（获取消息中的资源文件）→ 重新发布版本。

---

## ModuleNotFoundError: lark_oapi

守护进程用了系统 Python 而不是项目 venv。检查 plist/service 里的解释器路径必须是：

```
/path/to/feishu-claude-code/.venv/bin/python
```

提示：`ps` 显示的进程路径可能是 Homebrew Python 的真身路径（venv python 是软链接），**不代表** venv 没生效——以 `import lark_oapi` 是否成功为准。

---

## Address already in use

`CALLBACK_PORT`（默认 9981）被占。常见于手动启动与 launchd KeepAlive 互相打架，产生多个实例：

```bash
# 杀光所有实例和端口占用者，交给 launchd 统一管理
lsof -ti :9981 | xargs -r kill -9
ps aux | grep "feishu-claude-code/main.py" | grep -v grep | awk '{print $2}' | xargs -r kill -9
launchctl kickstart -k gui/$(id -u)/<你的服务label>
```

**原则**：托管方式二选一，手动调试前先 `launchctl bootout` 停掉守护。

---

## ngrok ERR_NGROK_9009

ngrok 认证会被 shell 的 `http_proxy` 环境变量干扰。本项目启动 ngrok 时已自动剥离代理变量；手动运行时：

```bash
unset http_proxy https_proxy && ngrok http 9981
```

另外查询本机 ngrok 4040 API 时也要绕过代理（代理会替 127.0.0.1 回 503），代码已用免代理 opener 处理。

---

## 错误追踪系统

以上都对不上号？bot 内置错误追踪：出错时用户会收到唯一错误 ID（如 `ERR-20260705-a3b4c5`），在飞书发送：

```
/error ERR-20260705-a3b4c5
```

即可查看完整错误详情（类型、调用栈、session、上下文）。错误档案存于 `~/.feishu-claude/errors/`。
