---
name: tokenmesh
description: >-
  Call LLMs through Tokenmesh (OpenAI-compatible gateway). Use when the user
  wants cost-aware routing, model=auto, BYOK setup, routing explain, or
  Tokenmesh API integration in code or curl.
---

# Tokenmesh — 一键接入

Tokenmesh 是 **OpenAI 兼容** 网关：`base_url` 指向 Tokenmesh，`model` 用 `auto`，自动选最便宜够用的模型。

## 开发者控制台

打开 **http://localhost:8080/** →「快速开始」注册拿 `tm_live_` Key → 复制 Python/curl 代码 →「省钱看板」看节省金额。

## 默认地址

| 环境 | Base URL |
|------|----------|
| 本地 | `http://localhost:8080/v1` |
| 生产 | 替换为你的部署地址 |

## API Token（每人一个）

```bash
# 注册（Key 只显示一次）
curl -s http://localhost:8080/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@co.com","password":"secret123"}'
# → api_key: tm_live_...
```

请求时带 `Authorization: Bearer tm_live_...`，用量记入该账号。

## 最小调用（Python）

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url=os.getenv("TOKENMESH_BASE_URL", "http://localhost:8080/v1"),
    api_key=os.environ["TOKENMESH_API_KEY"],  # tm_live_...
    default_headers={
        "X-DeepSeek-API-Key": os.environ["DEEPSEEK_API_KEY"],
        # 可选更多: X-OpenAI-API-Key, X-Qwen-API-Key, ...
    },
)

resp = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "用 Python 写快排"}],
)
print(resp.choices[0].message.content)
# 路由与省钱信息在响应 JSON 的 tokenmesh 字段
```

## 最小调用（curl）

```bash
export TOKENMESH_URL=http://localhost:8080
export TOKENMESH_API_KEY=tm_live_...
export DEEPSEEK_API_KEY=sk-...

curl -s "$TOKENMESH_URL/v1/chat/completions" \
  -H "Authorization: Bearer $TOKENMESH_API_KEY" \
  -H "Content-Type: application/json" \
  -H "X-DeepSeek-API-Key: $DEEPSEEK_API_KEY" \
  -d '{"model":"auto","messages":[{"role":"user","content":"你好"}]}'
```

## 免费看路由（不花 token）

```bash
curl -s -X POST "$TOKENMESH_URL/v1/routing/explain" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"写一个 Python 快排"}]}'
```

## 常用扩展字段

| 字段 / Header | 作用 |
|---------------|------|
| `model: "auto"` | 自动路由（推荐） |
| `x_tokenmesh_tier: "fast"` | 强制便宜档 |
| `x_tokenmesh_tier: "frontier"` | 强制高质量档 |
| `x_tokenmesh_model` | 钉死某个 tokenmesh 模型 key |
| `X-Tokenmesh-Project` | 使用项目级路由配置 |

## 环境变量速查

```bash
export TOKENMESH_BASE_URL=http://localhost:8080/v1
export TOKENMESH_API_KEY=tm_live_...
export DEEPSEEK_API_KEY=sk-...
# 可选
export OPENAI_API_KEY=sk-...
export QWEN_API_KEY=...
```

## 相关端点

- `POST /v1/chat/completions` — 主接口（与 OpenAI 相同）
- `POST /v1/routing/explain` — 路由解释（不调 LLM）
- `GET /v1/evolution/status` — 自我进化 / 省钱策略状态
- `GET /v1/usage/summary` — 用量与节省统计
- `GET /docs` — Swagger

## Agent 使用原则

1. 优先 `model=auto`，不要默认写死 `gpt-4o`。
2. 用户只提供一个 Key 时，只传对应 `X-{Provider}-API-Key` header。
3. 调试路由用 `/v1/routing/explain`，避免为试路由浪费 token。
4. 读响应里 `tokenmesh.routed_model`、`tokenmesh.savings` 向用户汇报省了多少钱。
