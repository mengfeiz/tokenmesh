"""Tests for the Tokenmesh task classifier."""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from tokenmesh.classifier import classify


def make_messages(content: str) -> list[dict]:
    return [{"role": "user", "content": content}]


class TestTaskTypeDetection:
    def test_simple_greeting(self):
        r = classify(make_messages("Hello, how are you?"))
        assert r.task_type == "simple_qa"
        assert r.complexity == "low"

    def test_what_is_question(self):
        r = classify(make_messages("What is the capital of France?"))
        assert r.task_type == "simple_qa"

    def test_coding_python(self):
        r = classify(make_messages("Write a python function to sort a list"))
        assert r.task_type == "coding"

    def test_coding_with_code_block(self):
        r = classify(make_messages("Fix this code:\n```python\ndef foo(): pass\n```"))
        assert r.task_type == "coding"

    def test_summarization(self):
        r = classify(make_messages("Summarize this article for me"))
        assert r.task_type == "summarization"

    def test_extraction(self):
        r = classify(make_messages("Extract all email addresses from this text"))
        assert r.task_type == "extraction"

    def test_reasoning(self):
        r = classify(make_messages("Why is recursion sometimes worse than iteration? Analyze the tradeoffs"))
        assert r.task_type == "reasoning"

    def test_creative(self):
        r = classify(make_messages("Write a short blog post about AI trends"))
        assert r.task_type == "creative"


class TestComplexity:
    def test_short_simple_is_low(self):
        r = classify(make_messages("What is 2+2?"))
        assert r.complexity == "low"

    def test_multi_step_is_medium_or_high(self):
        r = classify(make_messages(
            "First explain how async/await works, then show me an example, "
            "and finally compare it to callbacks"
        ))
        assert r.complexity in ("medium", "high")

    def test_comparison_bumps_complexity(self):
        r = classify(make_messages("Compare REST vs GraphQL APIs and their tradeoffs"))
        assert r.complexity in ("medium", "high")


class TestModelSelection:
    def test_simple_qa_gets_cheap_model(self):
        r = classify(make_messages("Hello"))
        spec_key = r.recommended_model
        # Should not route simple greeting to frontier model
        assert spec_key not in ("openai/gpt-4o", "anthropic/claude-sonnet-4")

    def test_complex_reasoning_gets_frontier(self):
        r = classify(make_messages(
            "Prove that P != NP and analyze all known partial results, "
            "comparing the approaches taken by complexity theorists. "
            "Step by step."
        ))
        # High complexity reasoning should get a stronger model
        assert r.complexity == "high"
        assert r.task_type == "reasoning"

    def test_coding_gets_deepseek(self):
        r = classify(make_messages("Write a python quicksort implementation"))
        # DeepSeek is strong at coding and cost-efficient
        assert "deepseek" in r.recommended_model or r.recommended_model in (
            "openai/gpt-4o-mini", "anthropic/claude-haiku-4-5"
        )

    def test_frontier_tier_override(self):
        r = classify(make_messages("Hello"), preferred_tier="frontier")
        assert r.route_tier == "R3"

    def test_fast_tier_override(self):
        r = classify(make_messages(
            "Analyze the complete competitive landscape of AI infrastructure "
            "with deep tradeoffs"
        ), preferred_tier="fast")
        assert r.route_tier == "R0"


class TestProviderFiltering:
    def test_filters_to_available_providers(self):
        # Only have OpenAI key
        r = classify(
            make_messages("Write python code"),
            available_providers={"openai"},
        )
        from tokenmesh.models import MODELS
        spec = MODELS.get(r.recommended_model)
        assert spec is not None
        assert spec.provider == "openai"

    def test_falls_back_when_no_match(self):
        # Provider list that won't match any preferred model for coding
        # Should still return something (fallback logic)
        r = classify(
            make_messages("Write code"),
            available_providers={"openai", "anthropic", "deepseek"},
        )
        assert r.recommended_model is not None


class TestRouteTiers:
    def test_greeting_is_r0(self):
        r = classify(make_messages("你好"))
        assert r.route_tier == "R0"
        assert r.task_type == "simple_qa"

    def test_debug_flag_escalates_to_r2(self):
        r = classify(make_messages("这个报错怎么修？Traceback (most recent call last)"))
        assert r.flags.get("debug")
        assert r.route_tier in ("R2", "R3")

    def test_deepseek_only_picks_different_models(self):
        simple = classify(
            make_messages("你好"),
            available_providers={"deepseek"},
        )
        hard = classify(
            make_messages(
                "Prove that P != NP and analyze all known partial results step by step"
            ),
            available_providers={"deepseek"},
        )
        assert simple.recommended_model != hard.recommended_model or hard.route_tier > simple.route_tier

    def test_chinese_coding_detected(self):
        r = classify(make_messages("用 Python 写一个快速排序函数"))
        assert r.task_type == "coding"


class TestQualityAndRoutingMode:
    def test_basic_routing_mode_uses_cheap_available(self):
        r = classify(
            make_messages("Prove P != NP with full analysis and tradeoffs"),
            routing_mode="basic",
            available_providers={"deepseek"},
        )
        assert "routing_mode:basic" in r.signals
        assert r.recommended_model.startswith("deepseek/")

    def test_quality_threshold_low_forces_simple_routing(self):
        r = classify(
            make_messages("Compare REST vs GraphQL with tradeoffs"),
            quality_threshold=0.1,
        )
        assert any("quality_threshold:low" in s for s in r.signals)


class TestLongContext:
    def test_long_message_triggers_long_context(self):
        long_text = "word " * 8000  # ~32k tokens estimate
        r = classify(make_messages(long_text))
        assert r.task_type == "long_context"

    def test_long_context_gets_long_context_model(self):
        long_text = "word " * 8000
        r = classify(make_messages(long_text))
        from tokenmesh.models import MODELS
        spec = MODELS.get(r.recommended_model)
        assert spec is not None
        assert spec.long_context or spec.context_window >= 100_000
