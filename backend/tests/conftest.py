"""Shared pytest fixtures."""

import pytest
from fastapi.testclient import TestClient

from gls.main import app


@pytest.fixture
def client() -> TestClient:
    """Create test client for API testing."""
    return TestClient(app)
