"""Integration tests for API endpoints."""

from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """Health endpoint should return healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_list_talks(client: TestClient) -> None:
    """List talks endpoint should return a list."""
    response = client.get("/api/v1/talks")
    assert response.status_code == 200
    data = response.json()
    assert "talks" in data
    assert isinstance(data["talks"], list)
