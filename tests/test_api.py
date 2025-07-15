"""Test cases for the Snipster API using FastAPI's TestClient and an in-memory repository."""

import pytest
from fastapi.testclient import TestClient

from snipster.api import app, get_repo
from snipster.models import Language
from snipster.repo import InMemorySnippetRepo


@pytest.fixture(autouse=True)
def inmemory_repo() -> InMemorySnippetRepo:
    """Fixture to provide an in-memory repository for testing."""
    memory_repo = InMemorySnippetRepo()
    app.dependency_overrides[get_repo] = lambda: memory_repo
    return memory_repo


@pytest.fixture
def client() -> TestClient:
    """Fixture to provide a FastAPI test client."""
    return TestClient(app)


def test_create_snippet(client: TestClient, inmemory_repo: InMemorySnippetRepo):  # type: ignore
    """Test creating a new snippet."""
    payload = {
        "title": "Test Snippet",
        "code": "print('Hello, World!')",
        "language": Language.PYTHON,
        "description": "A simple test snippet",
        "tags": "test,example",
    }
    response = client.post("/snippets/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Snippet"
    assert data["language"] == Language.PYTHON
    assert data["tags"] == "test,example"
    assert inmemory_repo.get(data["id"]) is not None  # type: ignore


def test_list_snippets(client: TestClient, inmemory_repo: InMemorySnippetRepo):
    """Test listing snippets."""
    # First, create a snippet
    payload = {
        "title": "Test Snippet",
        "code": "print('Hello, World!')",
        "language": Language.PYTHON,
        "description": "A simple test snippet",
        "tags": "test,example",
    }
    response = client.post("/snippets/", json=payload)

    # Now list snippets
    response = client.get("/snippets/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["title"] == "Test Snippet"


def test_get_snippet(client: TestClient, inmemory_repo: InMemorySnippetRepo):
    """Test getting a snippet by ID."""
    # First, create a snippet
    payload = {
        "title": "Test Snippet",
        "code": "print('Hello, World!')",
        "language": Language.PYTHON,
        "description": "A simple test snippet",
        "tags": "test,example",
    }
    response = client.post("/snippets/", json=payload)
    snippet_id = response.json()["id"]

    # Now get the snippet by ID
    response = client.get(f"/snippets/{snippet_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == snippet_id
    assert data["title"] == "Test Snippet"


def test_delete_snippet(client: TestClient, inmemory_repo: InMemorySnippetRepo):  # type: ignore
    """Test deleting a snippet by ID."""
    # First, create a snippet
    payload = {
        "title": "Test Snippet",
        "code": "print('Hello, World!')",
        "language": Language.PYTHON,
        "description": "A simple test snippet",
        "tags": "test,example",
    }
    response = client.post("/snippets/", json=payload)
    snippet_id = response.json()["id"]

    # Now delete the snippet by ID
    response = client.delete(f"/snippets/{snippet_id}")
    assert response.status_code == 200
    assert response.json() == {
        "message": f"Snippet with ID {snippet_id} deleted successfully."
    }


def test_favorite_snippet(client: TestClient, inmemory_repo: InMemorySnippetRepo):  # type: ignore
    """Test marking a snippet as favorite."""
    # First, create a snippet
    payload = {
        "title": "Test Snippet",
        "code": "print('Hello, World!')",
        "language": Language.PYTHON,
        "description": "A simple test snippet",
        "tags": "test,example",
    }
    response = client.post("/snippets/", json=payload)
    snippet_id = response.json()["id"]

    # Now favorite the snippet
    response = client.post(f"/snippets/{snippet_id}/favorite")
    assert response.status_code == 200
    assert response.json() == {"message": f"Snippet with ID {snippet_id} favorited"}

    # Verify the snippet is marked as favorite
    snippet = inmemory_repo.get(snippet_id)
    assert snippet.favorite is True


def test_search_snippets(client: TestClient, inmemory_repo: InMemorySnippetRepo):
    """Test searching for snippets."""
    # First, create a snippet
    payload = {
        "title": "Test Snippet",
        "code": "print('Hello, World!')",
        "language": Language.PYTHON,
        "description": "A simple test snippet",
        "tags": "test,example",
    }
    client.post("/snippets/", json=payload)
    # Now search for the snippet
    response = client.get(
        "/snippets/search/?term=Test Snippet&language=python"  # type: ignore,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0  # type: ignore
    assert data[0]["title"] == "Test Snippet"


def test_run_snippet(client: TestClient, inmemory_repo: InMemorySnippetRepo):  # type: ignore
    """Test running a snippet."""
    # First, create a snippet
    payload = {
        "title": "Test Snippet",
        "code": "print('Hello, World!')",
        "language": Language.PYTHON.value,  # type: ignore
        "description": "A simple test snippet",
        "tags": "test,example",
    }
    response = client.post("/snippets/", json=payload)
    snippet_id = response.json()["id"]

    # Now run the snippet
    response = client.post(f"/snippets/{snippet_id}/run")
    assert response.status_code == 200
    data = response.json()
    assert data["output"] == "Hello, World!\n"  # type: ignore


def test_404_codes(client: TestClient):  # type: ignore
    """Test 404 responses for non-existent snippets."""
    response = client.get("/snippets")
    assert response.status_code == 404
    response = client.get("/snippets/9999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Snippet not found"}
    response = client.delete("/snippets/9999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Snippet not found"}
