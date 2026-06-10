"""Tests for auth and project modules."""
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from tokenmesh.auth import AuthManager
from tokenmesh.projects import ProjectManager


@pytest.fixture
def temp_db(tmp_path):
    return tmp_path / "test.db"


def test_register_and_resolve_key(temp_db):
    auth = AuthManager(temp_db)
    result = auth.register("dev@tokenmesh.ai", "password123")
    raw_key = result["api_key"]
    assert raw_key.startswith("tm_live_")

    user = auth.resolve_api_key(raw_key)
    assert user is not None
    assert user.email == "dev@tokenmesh.ai"


def test_revoked_key_rejected(temp_db):
    auth = AuthManager(temp_db)
    result = auth.register("dev@tokenmesh.ai", "password123")
    user = auth.resolve_api_key(result["api_key"])
    keys = auth.list_api_keys(user.id)
    auth.revoke_api_key(user.id, keys[0]["id"])
    assert auth.resolve_api_key(result["api_key"]) is None


def test_project_crud(temp_db):
    auth = AuthManager(temp_db)
    projects = ProjectManager(temp_db)
    user = auth.register("dev@tokenmesh.ai", "password123")["user"]

    project = projects.create(
        user_id=user["id"],
        name="prod-app",
        quality_threshold=0.2,
        routing_mode="smart",
    )
    assert project.quality_threshold == 0.2

    updated = projects.update(project.id, user["id"], quality_threshold=0.9)
    assert updated.quality_threshold == 0.9
