# Tokenmesh

**Cost-aware LLM gateway with task-aware routing.**

One API key. Every request is automatically routed to the most cost-effective
model that can handle it. Drop-in replacement for the OpenAI API.

```
Your app → Tokenmesh → DeepSeek / Qwen / GPT-4o / Claude / Gemini
                  ↑ picks the cheapest model that can do the job
```

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
  classifier.py  — Rule-based task/complexity classifier
  models.py      — Model registry with pricing
  provider.py    — Async HTTP client for all providers (BYOK)
  keys.py        — BYOK header extraction
  config.py      — Pydantic settings
  cli.py         — uvicorn entry point
```

## Roadmap

- [ ] ML classifier v2 (train on routing data)
- [ ] Semantic cache (Redis + embeddings)
- [ ] Usage/savings SQLite log
- [ ] Stripe billing integration
- [ ] Multi-user API key management
- [ ] Docker Compose setup
