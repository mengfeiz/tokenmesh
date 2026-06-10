#!/usr/bin/env bash
# 一键调用 Tokenmesh（OpenAI 兼容）
# 用法: ./scripts/chat.sh "你的问题"
set -euo pipefail

BASE="${TOKENMESH_URL:-http://127.0.0.1:8080}"
PROMPT="${1:-你好}"

if [ -z "${DEEPSEEK_API_KEY:-}" ] && [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "请设置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY" >&2
  echo "示例: DEEPSEEK_API_KEY=sk-... ./scripts/chat.sh '写一个快排'" >&2
  exit 1
fi

HEADERS=(-H "Content-Type: application/json")
[ -n "${TOKENMESH_API_KEY:-}" ] && HEADERS+=(-H "Authorization: Bearer $TOKENMESH_API_KEY")
[ -n "${DEEPSEEK_API_KEY:-}" ] && HEADERS+=(-H "X-DeepSeek-API-Key: $DEEPSEEK_API_KEY")
[ -n "${OPENAI_API_KEY:-}" ]   && HEADERS+=(-H "X-OpenAI-API-Key: $OPENAI_API_KEY")
[ -n "${QWEN_API_KEY:-}" ]     && HEADERS+=(-H "X-Qwen-API-Key: $QWEN_API_KEY")

BODY=$(python3 -c "import json,sys; print(json.dumps({'model':'auto','messages':[{'role':'user','content':sys.argv[1]}]}))" "$PROMPT")

curl -sf -X POST "$BASE/v1/chat/completions" "${HEADERS[@]}" -d "$BODY" \
  | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(d['choices'][0]['message']['content'])
t=d.get('tokenmesh',{})
if t:
    print('---')
    print('model:', t.get('routed_model'))
    s=t.get('savings',{})
    if s: print('saved:', s.get('saved_usd'), 'USD (', s.get('savings_pct'), '%)', sep='')
"
