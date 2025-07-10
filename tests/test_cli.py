from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from snipster.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def db_setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Setup temporal database for each test"""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    yield


@pytest.fixture()
def add_snippet() -> Any:
    """Add a test snippet and return the result"""
    return runner.invoke(
        app,
        [
            "add",
            "Test Snippet",
            "print('hello')",
            "--language",
            "python",
            "--description",
            "A test",
            "--tag",
            "test",
        ],
    )


def test_add_snippet(add_snippet: Any):
    """Test adding a snippet"""
    assert add_snippet.exit_code == 0
    assert "Snippet 'Test Snippet' added" in add_snippet.output


def test_list_snippets(add_snippet: Any):
    """Test listing snippets when they exist"""
    # Primero agregar el snippet
    assert add_snippet.exit_code == 0

    # Luego listar
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "Test Snippet" in result.output


def test_delete_snippet(add_snippet: Any):
    # Verificar que el snippet se agregó correctamente
    assert add_snippet.exit_code == 0
    assert "Snippet 'Test Snippet' added" in add_snippet.output

    # Verificar que el snippet existe antes de intentar eliminarlo
    list_result = runner.invoke(app, ["list"])
    assert list_result.exit_code == 0
    assert "Test Snippet" in list_result.output

    # Ahora eliminar el snippet
    result = runner.invoke(
        app,
        [
            "delete",
            "1",
        ],
    )
    assert result.exit_code == 0
    assert "Snippet 1 deleted" in result.output

    result = runner.invoke(
        app,
        [
            "list",
        ],
    )
    assert "Test Snippet" not in result.output


def test_search_snippet(add_snippet: Any):
    """Test searching for snippets"""
    result = runner.invoke(
        app,
        [
            "add",
            "List Me",
            "ll = [1, 2, 3, 4]",
            "--language",
            "python",
            "--description",
            "List example",
            "--tag",
            "example",
        ],
    )
    assert result.exit_code == 0
    assert result.output == "Snippet 'List Me' added.\n"
    result = runner.invoke(
        app,
        [
            "search",
            "ist",
        ],
    )
    assert "List Me" in result.output

    # Buscar un snippet que no existe
    result = runner.invoke(app, ["search", "Non-existing"])
    assert result.exit_code == 0
    assert "Snippets not found" in result.output


def test_toggle_favorite(add_snippet: Any):
    """Test toggling favorite status"""
    # Primero agregar el snippet
    assert add_snippet.exit_code == 0

    # Marcar como favorito
    result = runner.invoke(app, ["toggle-favorite", "1"])
    assert result.exit_code == 0
    assert "favorited" in result.output

    # Desmarcar como favorito
    result = runner.invoke(app, ["toggle-favorite", "1"])
    assert result.exit_code == 0
    assert "unfavorited" in result.output


def test_toggle_favorite_not_found():
    """Test toggling favorite on non-existent snippet"""
    result = runner.invoke(app, ["toggle-favorite", "999"])
    assert result.exit_code == 0
    assert "Snippet 999 not found" in result.output


def test_tag_snippet(add_snippet: Any):
    """Test tagging a snippet"""
    # Primero agregar el snippet
    assert add_snippet.exit_code == 0

    # Agregar un tag
    result = runner.invoke(app, ["tag", "1", "newtag"])
    assert result.exit_code == 0
    assert "Tag 'newtag' added to snippet 1" in result.output

    # Verificar que el tag se aplicó (listar snippets)
    list_result = runner.invoke(app, ["list"])
    assert "Tags:" in list_result.output

    # Remover el tag
    result = runner.invoke(app, ["tag", "1", "newtag", "--remove"])
    assert result.exit_code == 0
    assert "Tag 'newtag' removed from snippet 1" in result.output


def test_tag_snippet_not_found():
    """Test tagging a non-existent snippet"""
    result = runner.invoke(app, ["tag", "999", "test"])
    assert result.exit_code == 0
    assert "Snippet 999 not found" in result.output


def test_delete_snippet_not_found():
    """Test deleting a non-existent snippet"""
    result = runner.invoke(app, ["delete", "999"])
    assert result.exit_code == 0
    assert "Snippet with id 999 not found" in result.output
