# Tokenmesh

**Cost-aware LLM gateway with task-aware routing.**

One API key. Every request is automatically routed to the most cost-effective
model that can handle it. Drop-in replacement for the OpenAI API.

```
Your app → Tokenmesh → DeepSeek / Qwen / GPT-4o / Claude / Gemini
                  ↑ picks the cheapest model that can do the job
```

## 30 秒试用（不需要任何 LLM API Key）

```bash
# 1. 安装并启动
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e .
tokenmesh   # 另开终端继续

# 2. 一键冒烟测试
chmod +x scripts/try.sh && ./scripts/try.sh

# 或手动：只看路由决策（不调用 LLM，零成本）
curl -s http://localhost:8080/v1/routing/explain \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"写一个 Python 快排"}]}' | python3 -m json.tool
```

**营销站 + 开发者控制台（推荐）：**

```bash
# 终端 1：API
source .venv/bin/activate && tokenmesh

# 终端 2：Next.js 前端
npm install && npm run dev
```

- 首页：**http://localhost:3000/**
- 开发者控制台：**http://localhost:3000/console**（注册 Key、复制代码、省钱看板）
- API 文档：http://localhost:8080/docs

也可直接访问 **http://localhost:8080/**（内置静态控制台，与 `/console` 功能相同）。

## 一键接入 Tokenmesh

**把 OpenAI SDK 的 `base_url` 换成 Tokenmesh，`api_key` 换成你的 `tm_live_` Key，`model` 写成 `auto`。** 其余代码不用改。

### 0. 获取你的 API Token（每人一个）

在 **http://localhost:8080/** 点「注册并获取 Key」，或调用 API：

```bash
curl -s http://localhost:8080/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@company.com","password":"your-password"}'
# 返回: { "api_key": "tm_live_xxxx...", "user": { ... } }
```

Key 只显示一次，请保存。后续请求带 `Authorization: Bearer tm_live_...`，用量会记到你的账号，可在「省钱看板」查看节省金额。

### 1. 环境变量（推荐）

```bash
export TOKENMESH_BASE_URL=http://localhost:8080/v1
export TOKENMESH_API_KEY=tm_live_...     # 注册时拿到
export DEEPSEEK_API_KEY=sk-...          # 至少一个供应商 Key（BYOK）
# 可选: OPENAI_API_KEY, QWEN_API_KEY, GOOGLE_API_KEY, ...
```

### 2. Python（3 行）

```python
from openai import OpenAI
import os

client = OpenAI(
    base_url=os.getenv("TOKENMESH_BASE_URL", "http://localhost:8080/v1"),
    api_key=os.environ["TOKENMESH_API_KEY"],
    default_headers={"X-DeepSeek-API-Key": os.environ["DEEPSEEK_API_KEY"]},
)

r = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "用 Python 写快排"}],
)
print(r.choices[0].message.content)
```

### 3. curl（一条命令）

```bash
TOKENMESH_API_KEY=tm_live_... DEEPSEEK_API_KEY=sk-... ./scripts/chat.sh "用 Python 写快排"
```

或手写：

```bash
curl -s http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer $TOKENMESH_API_KEY" \
  -H "Content-Type: application/json" \
  -H "X-DeepSeek-API-Key: $DEEPSEEK_API_KEY" \
  -d '{"model":"auto","messages":[{"role":"user","content":"你好"}]}'
```

### 4. Cursor / Claude Agent Skill

仓库自带 Skill，教 Agent 自动走 Tokenmesh：

```text
.cursor/skills/tokenmesh/SKILL.md
```

在 Cursor 中打开本项目即可被 Agent 发现；或复制到 `~/.cursor/skills/tokenmesh/` 全局使用。

### 5. 省钱看板

登录后打开控制台 **「省钱看板」** 标签，或带 Key 调 API：

```bash
curl -s "http://localhost:8080/v1/usage/summary?days=30" \
  -H "Authorization: Bearer $TOKENMESH_API_KEY"
```

返回累计节省金额、平均节省比例、按模型分布、最近请求等。

### 6. 最小 API 表

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/v1/auth/register` | 注册，返回 `tm_live_` API Key（仅一次） |
| `POST` | `/v1/auth/login` | 登录；`create_new_key: true` 可生成新 Key |
| `GET` | `/v1/me` | 当前用户、套餐、`api_base`（需 Bearer Key） |
| `POST` | `/v1/chat/completions` | **主接口**，与 OpenAI 完全兼容，`model=auto` |
| `POST` | `/v1/routing/explain` | 只看路由决策，**不调用 LLM、不花钱** |
| `GET` | `/v1/evolution/status` | 自我进化策略与预期节省 |
| `GET` | `/v1/usage/summary` | 用量与省钱统计（需 Bearer Key） |
| `GET` | `/v1/usage/recent` | 最近请求列表（需 Bearer Key） |
| `GET` | `/v1/models` | 支持的模型列表 |
| `GET` | `/health` | 健康检查 |

### 7. 响应里的 Tokenmesh 元数据

每次 `chat/completions` 响应会附带：

```json
{
  "tokenmesh": {
    "routed_model": "deepseek/deepseek-chat",
    "task_type": "coding",
    "route_tier": "R1",
    "evolved": false,
    "savings": {
      "actual_cost_usd": 0.000002,
      "baseline_cost_usd": 0.000042,
      "saved_usd": 0.000040,
      "savings_pct": 94.5
    }
  }
}
```

响应 Header：`X-Tokenmesh-Model`、`X-Tokenmesh-Savings-USD`、`X-Tokenmesh-Route-Tier`。

## Quickstart

```bash
# Install
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env — or pass keys per-request (BYOK)

# Run
tokenmesh
# or: uvicorn tokenmesh.app:app --port 8080
```

## Usage

### Drop-in replacement

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="any-string",          # unused in BYOK mode
    default_headers={
        "X-DeepSeek-API-Key": "your-deepseek-key",
        "X-OpenAI-API-Key":   "your-openai-key",
        "X-Qwen-API-Key":     "your-qwen-key",
    }
)

response = client.chat.completions.create(
    model="auto",     # Tokenmesh picks the model — or specify a tokenmesh model key
    messages=[{"role": "user", "content": "Write a Python quicksort"}]
)

# Response includes routing metadata
print(response.tokenmesh)
# {
#   "routed_model": "deepseek/deepseek-chat",
#   "task_type": "coding",
#   "complexity": "medium",
#   "savings": {
#     "actual_cost_usd": 0.0000023,
#     "baseline_cost_usd": 0.000042,
#     "saved_usd": 0.000040,
#     "savings_pct": 94.5,
#     "baseline_model": "openai/gpt-4o"
#   }
# }
```

### Explain routing (dry-run, no API call)

```bash
curl -X POST http://localhost:8080/v1/routing/explain \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Write a Python quicksort"}]
  }'
```

### Force a tier

```python
# Always use fast/cheap models
response = client.chat.completions.create(
    model="auto",
    messages=[...],
    extra_body={"x_tokenmesh_tier": "fast"}
)

# Always use frontier models
response = client.chat.completions.create(
    model="auto",
    messages=[...],
    extra_body={"x_tokenmesh_tier": "frontier"}
)
```

### Pin a specific model

```python
response = client.chat.completions.create(
    model="deepseek/deepseek-chat",   # exact Tokenmesh model key
    messages=[...]
)
```

## Supported Models

| Key | Model | Input $/1M | Output $/1M | Tier |
|-----|-------|-----------|------------|------|
| `openai/gpt-4o` | GPT-4o | $5.00 | $15.00 | frontier |
| `openai/gpt-4o-mini` | GPT-4o Mini | $0.15 | $0.60 | balanced |
| `anthropic/claude-sonnet-4` | Claude Sonnet 4 | $3.00 | $15.00 | frontier |
| `anthropic/claude-haiku-4-5` | Claude Haiku 4.5 | $0.80 | $4.00 | balanced |
| `deepseek/deepseek-chat` | DeepSeek V3 | $0.27 | $1.10 | balanced |
| `deepseek/deepseek-reasoner` | DeepSeek R1 | $0.55 | $2.19 | balanced |
| `qwen/qwen-max` | Qwen Max | $0.40 | $1.20 | balanced |
| `qwen/qwen-long` | Qwen Long (1M ctx) | $0.05 | $0.14 | fast |
| `qwen/qwen-turbo` | Qwen Turbo | $0.02 | $0.06 | fast |
| `google/gemini-flash-2` | Gemini 2.0 Flash | $0.10 | $0.40 | fast |
| `google/gemini-pro-2-5` | Gemini 2.5 Pro | $1.25 | $10.00 | frontier |
| `moonshot/moonshot-v1-128k` | Kimi 128k | $0.80 | $0.80 | balanced |

## BYOK Headers

Pass API keys per-request. No keys are stored.

```
X-OpenAI-API-Key:    sk-...
X-Anthropic-API-Key: sk-ant-...
X-DeepSeek-API-Key:  ...
X-Qwen-API-Key:      ...
X-Google-API-Key:    ...
X-Moonshot-API-Key:  ...
```

Or set platform keys in `.env` for managed mode.

## Routing Logic

Task classifier signals (v1, rule-based):

| Signal | Task type | Example |
|--------|-----------|---------|
| `what is`, `who is`, short greeting | `simple_qa` | "What is the capital of France?" |
| code blocks, `def`, `import`, `sql` | `coding` | "Write a Python quicksort" |
| `summarize`, `tl;dr`, `key points` | `summarization` | "Summarize this article" |
| `extract`, `parse`, `find all` | `extraction` | "Extract all emails" |
| `prove`, `analyze`, `tradeoffs` | `reasoning` | "Compare REST vs GraphQL" |
| `write a`, `story`, `blog`, `email` | `creative` | "Write a marketing email" |
| message > 30k tokens | `long_context` | Document analysis |

Complexity scored by: token length, multi-step indicators, comparison language.

## Run Tests

```bash
pytest tests/ -v
```

## Architecture

```
src/tokenmesh/
  app.py         — FastAPI gateway, routing orchestration
  auth.py        — Email/password + API key management
  projects.py    — Per-project routing configuration
  classifier.py  — Rule-based task/complexity classifier
  models.py      — Model registry with pricing
  provider.py    — Async HTTP client for all providers (BYOK)
  cache.py       — Semantic cache (optional embeddings)
  usage.py       — SQLite usage/savings log
  billing.py     — Stripe subscriptions
  status.py      — Provider health dashboard
  keys.py        — BYOK header extraction
  config.py      — Pydantic settings
  cli.py         — uvicorn entry point
```

## Auth & Projects

```bash
# Register (returns API key — save it)
curl -X POST http://localhost:8080/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"your-password"}'

# Use your Tokenmesh key
curl http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer tm_live_..." \
  -H "X-DeepSeek-API-Key: ..." \
  -d '{"model":"auto","messages":[{"role":"user","content":"Hello"}]}'
```

Create a project to tune cost vs quality per app:

```bash
curl -X POST http://localhost:8080/v1/projects \
  -H "Authorization: Bearer tm_live_..." \
  -H "Content-Type: application/json" \
  -d '{"name":"my-app","quality_threshold":0.3,"routing_mode":"smart"}'
```

Pass `X-Tokenmesh-Project: proj_xxx` on requests to apply project routing rules.

## Plans (PRD-aligned)

| Tier | Price | Routing | Cache |
|------|-------|---------|-------|
| Free | $0 | Smart + 自我进化 | 精确匹配缓存 |
| Pro | $9/mo | Smart + 自我进化 | 语义缓存 |
| Business | $79/mo | Smart + teams/SSO (roadmap) | 语义缓存 |

Upgrade via `POST /v1/billing/checkout`. Savings dashboard: `GET /v1/usage/summary`.

## Provider status

```bash
curl http://localhost:8080/v1/status/providers
```

## Docker

```bash
docker compose up --build
```

## Roadmap

- [x] Usage/savings SQLite log
- [x] Stripe billing integration
- [x] API key management
- [x] Per-project routing config
- [x] Semantic cache (in-memory; optional embeddings)
- [x] Docker Compose setup
- [x] Self-evolution flywheel (usage → learned tier downgrade)
- [x] Token optimizer (tier max_tokens + context trim)
- [ ] ML classifier v3 (train on routing data)
- [ ] Managed mode billing (5–8% markup)
- [ ] Redis-backed semantic cache
