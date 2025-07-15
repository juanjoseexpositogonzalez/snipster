from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlmodel import SQLModel, create_engine
from sqlmodel.pool import StaticPool
from typer.testing import CliRunner

from snipster.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def db_setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Setup temporal database for each test"""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Importante para SQLite en tests
        echo=False,
    )

    # Crear las tablas
    SQLModel.metadata.create_all(engine)

    yield engine

    # Cleanup: cerrar todas las conexiones
    engine.dispose()


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
    assert add_snippet.exit_code == 0
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


def test_run_code_success(add_snippet: Any):
    """Test running code"""
    # Primero agregar el snippet
    assert add_snippet.exit_code == 0
    all_snippets = runner.invoke(app, ["list"])
    assert all_snippets.exit_code == 0

    # Ejecutar el código del snippet
    result = runner.invoke(
        app,
        ["run", "1", "--version", "3.10.0"],  # type: ignore
    )

    assert result.exit_code == 0
    assert "hello" in result.output


def test_run_code_not_found():
    """Test running code for a non-existent snippet"""
    result = runner.invoke(app, ["run", "999"])
    assert result.exit_code == 0
    assert "Snippet with id 999 not found" in result.output


def test_run_code_raises_httperror(add_snippet: Any):
    """Test running code raises HTTPError"""
    # Primero agregar el snippet
    assert add_snippet.exit_code == 0

    # Mockear httpx.AsyncClient para que devuelva un status code != 200
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_client.return_value.__aenter__.return_value.post.return_value = (
            mock_response
        )

        # Ahora sí debería fallar
        result = runner.invoke(app, ["run", "1", "--version", "latest"])
        assert result.exit_code == 1  # Asumiendo que manejas el error apropiadamente


@patch("snipster.cli.httpx.AsyncClient")  # Reemplaza 'tu_modulo' con el nombre real
def test_run_code_displays_stderr(mock_client_class: Any, add_snippet: Any):
    """Test that stderr is displayed when present"""
    assert add_snippet.exit_code == 0

    # Mock de la respuesta
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "run": {"stdout": "", "stderr": "Error: variable not defined", "output": ""}
    }

    # Configurar el mock
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client_class.return_value.__aenter__.return_value = mock_client

    result = runner.invoke(app, ["run", "1"])

    print(f"Result output: '{result.output}'")  # Debug
    print(f"Exit code: {result.exit_code}")  # Debug

    assert result.exit_code == 0
    assert "STDERR:" in result.output
    assert "Error: variable not defined" in result.output


def test_create_image(add_snippet: Any):
    """Test creating an image from a snippet"""
    assert add_snippet.exit_code == 0

    # Mockear la función create_code_image
    with patch("snipster.cli.create_code_image") as mock_create_image:
        mock_create_image.return_value = "path/to/image.png"

        result = runner.invoke(app, ["image", "1"])

        assert result.exit_code == 0
        assert "Image for snippet 'Test Snippet' created successfully!" in result.output
        mock_create_image.assert_called_once()  # Verificar que se llamó a la función
