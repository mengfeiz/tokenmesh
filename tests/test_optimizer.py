"""Tests for request optimizer."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from tokenmesh.classifier import classify
from tokenmesh.optimizer import optimize_request, TIER_MAX_TOKENS


def test_r0_caps_max_tokens():
    c = classify([{"role": "user", "content": "你好"}])
    out = optimize_request([{"role": "user", "content": "你好"}], c, None)
    assert out.max_tokens == TIER_MAX_TOKENS["R0"]


def test_trims_long_history_for_simple_qa():
    messages = [{"role": "system", "content": "sys"}]
    for i in range(10):
        messages.append({"role": "user", "content": f"msg {i}"})
        messages.append({"role": "assistant", "content": f"reply {i}"})
    c = classify([{"role": "user", "content": "什么是 Tokenmesh?"}])
    out = optimize_request(messages, c, 2000)
    assert out.meta.get("trimmed_history") is True
    assert len(out.messages) < len(messages)
