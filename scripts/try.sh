#!/usr/bin/env bash
# Tokenmesh 30-second smoke test (no provider API keys required)
set -euo pipefail

BASE="${TOKENMESH_URL:-http://127.0.0.1:8080}"

echo "==> Health"
curl -sf "$BASE/health" | python3 -m json.tool

echo ""
echo "==> Provider status"
curl -sf "$BASE/v1/status/providers" | python3 -m json.tool | head -30

echo ""
echo "==> Routing explain (dry-run, no LLM call)"
curl -sf -X POST "$BASE/v1/routing/explain" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Write a Python quicksort"}]}' \
  | python3 -m json.tool

echo ""
echo "==> Register test user (optional — saves tm_live_ key)"
REGISTER=$(curl -sf -X POST "$BASE/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"try-$(date +%s)@example.com\",\"password\":\"try-tokenmesh\"}" || true)
if [ -n "$REGISTER" ]; then
  echo "$REGISTER" | python3 -m json.tool
  echo ""
  echo "Tip: export TOKENMESH_KEY=\$(echo '$REGISTER' | python3 -c \"import sys,json; print(json.load(sys.stdin)['api_key'])\")"
else
  echo "(register skipped — server may be down or email taken)"
fi

echo ""
echo "Done. For a real LLM call, add BYOK headers and POST /v1/chat/completions with model=auto."
