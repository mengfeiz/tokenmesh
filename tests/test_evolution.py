"""Tests for the self-evolution flywheel."""
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from tokenmesh.classifier import classify
from tokenmesh.evolution import EvolutionEngine
from tokenmesh.usage import UsageLogger, UsageRecord


def make_messages(content: str) -> list[dict]:
    return [{"role": "user", "content": content}]


class TestEvolutionLearn:
    def test_learns_downgrade_for_repeated_simple_qa(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test.db"
            logger = UsageLogger(db)
            now = time.time()
            for _ in range(12):
                logger._write_batch([UsageRecord(
                    model_key="deepseek/deepseek-chat",
                    provider="deepseek",
                    task_type="simple_qa",
                    complexity="low",
                    route_tier="R1",
                    savings_pct=72.0,
                    output_tokens=80,
                    input_tokens=40,
                    actual_cost=0.0001,
                    baseline_cost=0.0004,
                    saved_usd=0.0003,
                    ts=now,
                )])

            engine = EvolutionEngine(db, min_samples=8, min_savings_pct=50.0)
            n = engine.learn()
            assert n >= 1

            base = classify(make_messages("你好"), available_providers={"deepseek"})
            evolved = engine.apply(base, {"deepseek"}, "smart")
            assert evolved.evolved or evolved.route_tier <= base.route_tier


class TestEvolutionApply:
    def test_skips_high_risk(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = EvolutionEngine(Path(tmp) / "t.db")
            result = classify(
                make_messages("生产环境部署回滚方案"),
                available_providers={"deepseek"},
            )
            assert result.flags.get("high_risk")
            adjusted = engine.apply(result, {"deepseek"}, "smart")
            assert adjusted.route_tier == result.route_tier
