# feishu-claude-code

**在飞书里随时随地指挥你本机的 Claude Code。**

躺在沙发上 review 代码、通勤路上让 Claude 修 bug、饭桌上用手机审批 Plan——你的电脑在跑，你的人在哪都行。

> 复用 Claude Max/Pro 订阅，**不需要 API Key，不需要公网 IP，不需要服务器**。

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue" alt="Python" />
  <img src="https://img.shields.io/badge/Claude_Code-CLI-blueviolet" alt="Claude Code" />
  <img src="https://img.shields.io/badge/中国大陆网络-开箱即用-red" alt="CN Ready" />
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT" />
</p>

```
你（飞书，任何设备） ←── WebSocket ──→ 你的电脑（本项目） ──→ claude CLI（Max 订阅）
```

---

## 为什么选这个版本

本项目基于 [joewongjc/feishu-claude-code](https://github.com/joewongjc/feishu-claude-code) 增强，在保留全部上游能力的基础上，重点解决了**真实使用中最折磨人的问题**：

| 增强 | 解决什么痛点 |
|------|-------------|
| 🇨🇳 **大陆网络开箱即用** | Anthropic 对大陆 IP 返回 `403 Request not allowed`，而守护进程拿不到你 shell 里的代理变量。一行 `CLAUDE_PROXY` 配置，只给 claude 子进程注入代理，飞书 API 仍走国内直连 |
| 🧹 **环境变量自动净化** | 从配置过 LLM 网关的终端启动时，`ANTHROPIC_*` 变量会让 CLI 弃用订阅登录态——自动剥离，双保险 |
| 🔍 **全链路透明日志** | 每次调用记录完整命令行、result 事件（`is_error`/耗时/费用/回复预览）、退出码。出问题时日志直接告诉你答案，而不是一句干巴巴的"完成" |
| 🆔 **智能错误追踪** | 出错自动生成唯一错误 ID（`ERR-20260705-a3b4c5`），用户把 ID 发回来，`/error <ID>` 秒查完整调用栈和上下文，告别"你再复现一下我看看" |
| 📖 **实战排查手册** | [docs/troubleshooting.md](docs/troubleshooting.md) 收录生产环境真实踩坑，按报错对号入座 |

---

## 它长什么样

**流式输出**：Claude 边想边打字，工具调用（Bash / Read / Edit / Grep…）进度实时可见，不是等半天甩你一坨。

**交互按钮**：Claude 给出选项时自动渲染成可点击按钮——Y/N 确认、编号选择、Plan 审批，拇指一按就行。

**跨设备接力**：电脑上 debug 到一半要出门？`handover.py` 一键把终端会话移交到飞书，手机上无缝继续。

**群聊隔离**：每个群独立 session、独立模型、独立工作目录。`/ws` 给不同群绑定不同项目，多群并发互不打架。

---

## 5 分钟跑起来

### 前置条件

| 依赖 | 要求 | 验证命令 |
|------|------|---------|
| Python | 3.11+ | `python3 --version` |
| Claude Code CLI | 最新版 | `claude --version` |
| Claude Max/Pro 订阅 | 已登录 | `claude "hi"` 能正常回复 |
| 出境代理（仅大陆） | 本机 HTTP 代理 | `curl -x http://127.0.0.1:<端口> https://api.anthropic.com -o /dev/null -w "%{http_code}"` 非 403 |

### 第一步：安装

```bash
git clone https://github.com/idonecc/feishu-claude-code.git
cd feishu-claude-code

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
```

### 第二步：创建飞书应用（约 3 分钟）

1. 打开[飞书开放平台](https://open.feishu.cn/app) → 「创建企业自建应用」，起个名字（比如 `Claude`）
2. 「添加应用能力」→ 添加 **机器人**
3. 「权限管理」→ 开启这三个权限：

   | 权限 | 用途 |
   |------|------|
   | `im:message` | 收发消息 |
   | `im:message:send_as_bot` | 以机器人身份发消息 |
   | `im:resource` | 下载消息里的图片（想让 Claude 看截图必开） |

4. 「事件与回调」→「事件配置」→ 订阅方式选 **长连接**（不是 Webhook！这就是不需要公网 IP 的原因）→ 添加事件 `im.message.receive_v1`
5. 「凭证与基础信息」→ 复制 App ID 和 App Secret，填进 `.env`
6. 「版本管理与发布」→ 创建版本 → 管理员审核通过

### 第三步：配置 `.env`

```ini
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxx

DEFAULT_MODEL=claude-sonnet-4-6
DEFAULT_CWD=~/your-project        # Claude 默认在哪个目录干活

# ⚠️ 中国大陆用户必填，否则会撞 403（见下方疑难排查）
CLAUDE_PROXY=http://127.0.0.1:10808
```

### 第四步：启动

```bash
python3 main.py
```

看到这两行就成了：

```
🚀 飞书 Claude Bot 启动中...
✅ 连接飞书 WebSocket 长连接（自动重连）...
```

打开飞书，给机器人发一句「你好」——收到流式回复，收工。

---

## 日常使用

私聊直接说话；群聊 **@机器人** 说话（不 @ 的消息会被静默忽略，不打扰群友）。

输入 `/` 会弹出按钮菜单，不用背命令。速查表：

### 会话

| 命令 | 说明 |
|------|------|
| `/new` | 开新会话 |
| `/new plan` | 开新会话并进入 Plan 模式（只规划不动手） |
| `/resume` | 列出历史会话，按钮点选恢复 |
| `/stop` | 停掉当前正在跑的任务 |
| `/status` | 当前会话信息（模型/目录/session） |

### 模型与权限

| 命令 | 说明 |
|------|------|
| `/model opus` / `sonnet` / `haiku` | 切换模型 |
| `/mode bypass` | 跳过所有确认（默认，个人使用推荐） |
| `/mode plan` | 只出方案不执行 |
| `/mode default` | 敏感操作逐一确认 |

### 工作目录与工作空间

| 命令 | 说明 |
|------|------|
| `/cd ~/project` | 切换工作目录 |
| `/ls` | 看目录内容 |
| `/ws save api ~/projects/api` | 把目录存成命名工作空间 |
| `/ws use api` | 当前会话绑定到工作空间 |
| `/ws list` / `/ws remove api` | 列出 / 删除 |

### 查询与诊断

| 命令 | 说明 |
|------|------|
| `/usage` | Claude Max 用量和重置时间（macOS） |
| `/skills` / `/mcp` | 已装 Skills / MCP Servers |
| `/error ERR-xxx` | 🆕 按错误 ID 查完整错误详情 |
| `/help` | 帮助 |

### Skills 透传

`/commit`、`/review` 等未注册的斜杠命令会直接转发给 claude CLI——你在终端里能用的 Skill，飞书里同样能用。

### 发图片

直接把截图丢给机器人，Claude 会自动下载并分析。报错截图、UI 设计稿、监控面板都行。

### CLI Handover：终端 → 手机无缝接力

```bash
python3 handover.py "对话中的一段独特文本"
```

脚本在 `~/.claude/projects/` 里找到匹配的 session，通知飞书 Bot 切换过去。电脑前调试到一半，出门手机继续。

---

## 环境变量总览

| 变量 | 必填 | 默认值 | 说明 |
|------|:---:|-------|------|
| `FEISHU_APP_ID` | ✅ | - | 飞书应用 App ID |
| `FEISHU_APP_SECRET` | ✅ | - | 飞书应用 App Secret |
| `CLAUDE_PROXY` | 大陆✅ | 空 | claude 子进程出境代理，如 `http://127.0.0.1:10808`。**只注入 claude 子进程，飞书 API 不受影响**。海外留空 |
| `DEFAULT_MODEL` | | `claude-opus-4-6` | 默认模型 |
| `DEFAULT_CWD` | | `~` | 默认工作目录 |
| `PERMISSION_MODE` | | `bypassPermissions` | 工具权限模式 |
| `STREAM_CHUNK_SIZE` | | `20` | 流式推送字符阈值 |
| `CLAUDE_CLI_PATH` | | 自动查找 | claude 可执行文件路径 |
| `CALLBACK_PORT` | | `9981` | 卡片按钮回调端口 |
| `NGROK_DOMAIN` | | 空 | ngrok 固定域名，重启后回调 URL 不变 |

### 卡片按钮回调（可选）

按钮点击需要飞书能回调到你本机，用 ngrok 暴露 `CALLBACK_PORT` 即可，bot 启动时会自动拉起 ngrok 并打印回调地址。**不配置也不影响核心功能**——按钮点不动，手动输命令就行。

---

## 常驻部署

### macOS（launchd，推荐）

```bash
cp deploy/feishu-claude.plist ~/Library/LaunchAgents/com.feishu-claude.bot.plist
# 编辑 plist：把解释器路径改成 <项目路径>/.venv/bin/python（⚠️ 必须用 venv，否则 ModuleNotFoundError）

launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.feishu-claude.bot.plist
launchctl list | grep feishu-claude
```

### Linux（systemd）

```bash
sudo cp deploy/feishu-claude.service /etc/systemd/system/
# 编辑 service：改路径和 User，同样用 .venv/bin/python

sudo systemctl daemon-reload
sudo systemctl enable --now feishu-claude
journalctl -u feishu-claude -f
```

服务崩溃自动重启；内置看门狗每 4 小时主动重启刷新 WebSocket，防假死。

> **大陆用户再次提醒**：守护进程环境里没有你 shell 的代理变量，`.env` 里的 `CLAUDE_PROXY` 就是为这个场景准备的——别跳过。

---

## 架构与工作原理

```
┌──────────┐  WebSocket  ┌────────────────┐  subprocess  ┌────────────┐
│  飞书 App │◄───────────►│ feishu-claude  │─────────────►│ claude CLI │
│  (用户)   │  长连接      │  (main.py)     │ stream-json  │  (本机)     │
└──────────┘             └────────────────┘              └────────────┘
                                 │
                 ┌───────────┬───┴────────┬───────────┐
                 │           │            │           │
           ┌─────▼────┐ ┌───▼──────┐ ┌───▼──────┐ ┌──▼─────────┐
           │ commands │ │ session  │ │ feishu   │ │ error      │
           │ 命令路由  │ │ store    │ │ client   │ │ tracker 🆕 │
           └──────────┘ └──────────┘ └──────────┘ └────────────┘
```

1. 飞书通过 WebSocket 长连接把消息推到本机（所以不需要公网 IP）
2. bot 调用 `claude --print --output-format stream-json`，**spawn 前剥离 `ANTHROPIC_*` 污染变量、注入 `CLAUDE_PROXY`**
3. 解析 stream-json 事件流，文本增量和工具调用实时 PATCH 到飞书卡片
4. 每个聊天独立消息队列锁，多群并发安全
5. 任何异常自动生成错误 ID 归档到 `~/.feishu-claude/errors/`

---

## 疑难排查

最高频问题一张表，完整手册见 **[docs/troubleshooting.md](docs/troubleshooting.md)**：

| 症状 | 一句话原因 | 解法 |
|------|-----------|------|
| 回复 `403 Request not allowed` | 大陆 IP 被 Anthropic 封锁 **或** 环境里有 `ANTHROPIC_*` 网关变量（报错一字不差！） | `.env` 配 `CLAUDE_PROXY`；变量净化已内置 |
| `/` 有反应但提问就报错 | `/` 是本地处理，提问才走 Claude API | 同上，查 API 链路 |
| 发图片报 403 | 飞书应用缺 `im:resource` 权限 | 开权限 + 重新发布版本 |
| `ModuleNotFoundError: lark_oapi` | 守护进程用了系统 Python | plist/service 改用 `.venv/bin/python` |
| `Address already in use` | 手动启动和守护进程打架 | 杀光实例，托管方式二选一 |
| ngrok `ERR_NGROK_9009` | shell 代理变量干扰 ngrok 认证 | 已内置剥离；手动跑加 `unset http_proxy https_proxy` |

**快速鉴别 403 根因**：`curl -s --noproxy '*' -o /dev/null -w "%{http_code}" https://api.anthropic.com/v1/messages -X POST -d '{}'` → 返回 `403` 是地区封锁，返回 `401` 说明链路正常另有原因。

---

## 致谢

基于 [joewongjc/feishu-claude-code](https://github.com/joewongjc/feishu-claude-code) 二次开发，上游把流式卡片、session 管理、交互按钮这些硬骨头啃得很漂亮，本项目站在它的肩膀上补齐了大陆网络适配与可观测性。

## License

[MIT](LICENSE)
