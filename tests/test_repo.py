import json
import tempfile
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Sequence

import pytest
from sqlmodel import Session, SQLModel, create_engine

from src.snipster.exceptions import SnippetNotFoundError
from src.snipster.models import Language, Snippet
from src.snipster.repo import (
    DateTimeEncoder,
    DBSnippetRepo,
    InMemorySnippetRepo,
    JSONSnippetRepo,
    SnippetRepository,
)


def test_cannot_instantiate_abstract_repo():
    """Test that we cannot instantiate the abstract SnippetRepository class."""
    with pytest.raises(TypeError) as excinfo:
        SnippetRepository()  # type: ignore
    assert (
        "Can't instantiate abstract class SnippetRepository without an implementation for abstract methods 'add', 'delete', 'get', 'list'"
        in str(excinfo.value)
    )


def test_cannot_subclass_without_all_methods_implemented():
    """Test that we cannot subclass SnippetRepository without implementing all abstract methods."""

    class IncompleteRepo(SnippetRepository):  # type: ignore
        def add(self, snippet: Snippet) -> Snippet:  # type: ignore
            pass

        def list(self) -> Sequence[Snippet]:  # type: ignore
            pass

    with pytest.raises(TypeError) as excinfo:
        IncompleteRepo()  # type: ignore
    assert (
        "Can't instantiate abstract class IncompleteRepo without an implementation for abstract methods 'delete', 'get'"
        in str(excinfo.value)
    )


@pytest.fixture
def example_snippet() -> Snippet:
    """Fixture to create an example Snippet instance."""
    return Snippet(
        title="Test",
        code="print('hi')",
        language=Language.PYTHON,
    )


@pytest.fixture
def example_snippets() -> Sequence[Snippet]:
    """Fixture to create a sequence of example Snippet instances."""
    return [
        Snippet(
            title="print to stdout",
            code="print('hello world')",
            language=Language.PYTHON,
        ),
        Snippet(
            title="get user input",
            code="input('Enter city: ')",
            language=Language.PYTHON,
        ),
        Snippet(
            title="random number",
            code="let _ = nums.choose(&mut rng);",
            language=Language.RUST,
        ),
    ]


def test_full_in_mem_implementation(example_snippet: Snippet):
    """Test the full in-memory implementation of SnippetRepository."""
    repo = InMemorySnippetRepo()  # type: ignore
    repo.add(example_snippet)
    assert len(repo.list()) == 1
    retrieved = repo.get(1)
    assert retrieved.title == "Test"  # type: ignore
    assert retrieved.code == "print('hi')"  # type: ignore
    with pytest.raises(SnippetNotFoundError):
        repo.delete(2)
    repo.delete(1)
    assert len(repo.list()) == 0
    assert repo.get(1) is None


@pytest.fixture
def engine():
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):  # type: ignore
    """Fixture to create a SQLModel session."""
    session = Session(engine)  # type: ignore
    yield session
    session.rollback()
    session.close()


def test_db_implementation(session, example_snippet: Snippet):  # type: ignore
    """Test the database implementation of SnippetRepository."""
    repo = DBSnippetRepo(session)  # type: ignore
    repo.add(example_snippet)
    assert len(repo.list()) == 1
    assert repo.get(1).title == "Test"
    repo.delete(1)
    assert len(repo.list()) == 0
    with pytest.raises(SnippetNotFoundError):
        repo.get(1)
    with pytest.raises(SnippetNotFoundError):
        repo.delete(1)


def test_datetime_encoder_encodes_datetime():
    now = datetime(2024, 1, 1, 12, 0, 0)
    result = json.dumps({"now": now}, cls=DateTimeEncoder)
    assert "2024-01-01T12:00:00" in result


def test_datetime_encoder_fallback():
    class Dummy:
        pass

    dummy = Dummy()
    with pytest.raises(TypeError):
        json.dumps(dummy, cls=DateTimeEncoder)


def test_load_snippets_returns_empty_when_file_missing_or_empty():
    with TemporaryDirectory() as tmpdir:
        file = Path(tmpdir) / "empty.json"
        # Caso archivo no existe
        repo = JSONSnippetRepo(file)  # type: ignore
        assert repo._load() == []  # type: ignore

        # Caso archivo vacío
        file.touch()
        assert repo._load() == []  # type: ignore


def test_add_snippet_with_id_triggers_else_path(monkeypatch, example_snippet):  # type: ignore
    example_snippet.id = 99  # Forzar el else

    with TemporaryDirectory() as tmpdir:
        json_path = Path(tmpdir) / "snippets.json"
        monkeypatch.setenv("SNIPPET_JSON_FILE", str(json_path))

        repo = JSONSnippetRepo(json_path)  # type: ignore
        repo.add(example_snippet)  # type: ignore

        data = json.loads(json_path.read_text())
        assert data[0]["id"] == 99


def test_delete_raises_if_snippet_not_found(monkeypatch):  # type: ignore
    with TemporaryDirectory() as tmpdir:
        file = Path(tmpdir) / "snippets.json"
        file.write_text(
            json.dumps(
                [{"id": 1, "title": "Test", "code": "print(1)", "language": "python"}]
            )
        )

        monkeypatch.setenv("SNIPPET_JSON_FILE", str(file))
        repo = JSONSnippetRepo(file)  # type: ignore

        with pytest.raises(SnippetNotFoundError) as excinfo:
            repo.delete(999)

        assert "Snippet with ID 999 not found." in str(excinfo.value)


def test_json_implementation(example_snippet: Snippet):
    """Test the JSON implementation of SnippetRepository."""
    example_snippet.id = 1  # Set an ID for the example snippet
    with tempfile.TemporaryDirectory() as tempdir:
        json_file = Path(tempfile.mktemp(suffix=".json", dir=tempdir))
        repo = JSONSnippetRepo(json_file)  # type: ignore

        # Add a snippet

        repo.add(example_snippet)
        assert len(repo.list()) == 1

        # Retrieve the snippet
        retrieved = repo.get(1)
        assert retrieved.title == "Test"

        # Delete the snippet
        repo.delete(1)
        assert len(repo.list()) == 0

        # Ensure deletion works correctly
        with pytest.raises(SnippetNotFoundError):
            repo.delete(1)


@pytest.fixture
def repo(backend: str, request: str) -> SnippetRepository:
    """Fixture to provide the appropriate SnippetRepository based on the backend."""
    if backend == "db":
        return DBSnippetRepo(request.getfixturevalue("session"))  # type: ignore
    elif backend == "json":
        path = Path(tempfile.mktemp(suffix=".json"))
        return JSONSnippetRepo(path)  # type: ignore
    return InMemorySnippetRepo()  # type: ignore


@pytest.fixture
def add_snippets(repo: SnippetRepository, example_snippets: Sequence[Snippet]) -> None:
    """Fixture to add a snippet to the repository."""
    for snippet in example_snippets:
        repo.add(snippet)


@pytest.mark.parametrize("backend", ["in_memory", "db", "json"])
def test_search_snippet(
    backend: str, repo: SnippetRepository, add_snippets: Sequence[Snippet]
) -> None:
    assert len(repo.search("print")) == 1
    assert len(repo.search("input")) == 1
    assert len(repo.search("random")) == 1
    assert len(repo.search("notfound")) == 0
    assert len(repo.search("do")) == 2
    assert len(repo.search("Do")) == 2
    # Search by language
    assert len(repo.search("print", language=Language.PYTHON)) == 1
    assert len(repo.search("print", language=Language.RUST)) == 0
    assert len(repo.search("do", language=Language.RUST)) == 1
    assert len(repo.search("do", language=Language.PYTHON)) == 1


@pytest.mark.parametrize("backend", ["in_memory", "db", "json"])
def test_favorite_snippet(
    backend: str, repo: SnippetRepository, add_snippets: Sequence[Snippet]
) -> None:
    """Test favoriting a snippet."""
    snippet = repo.get(1)
    assert snippet is not None
    assert snippet.favorite is False
    repo.toggle_favorite(1)
    snippet = repo.get(1)
    assert snippet is not None
    assert snippet.favorite is True
    repo.toggle_favorite(1)
    snippet = repo.get(1)
    assert snippet is not None
    assert snippet.favorite is False
    with pytest.raises(SnippetNotFoundError):
        repo.toggle_favorite(999)


@pytest.mark.parametrize("backend", ["in_memory", "db", "json"])
def test_tag_snippet(
    backend: str, repo: SnippetRepository, add_snippets: Sequence[Snippet]
) -> None:
    """Test tagging a snippet."""
    repo.tag(1, "test")
    snippet = repo.get(1)
    assert snippet is not None
    assert snippet.tag_list == ["test"]
    repo.tag(1, "test")
    snippet = repo.get(1)
    assert snippet is not None
    assert snippet.tag_list == ["test"]
    repo.tag(1, "test2")
    snippet = repo.get(1)
    assert snippet is not None
    assert snippet.tag_list == ["test", "test2"]
    repo.tag(1, "test", "test2")
    snippet = repo.get(1)
    assert snippet is not None
    assert snippet.tag_list == ["test", "test2"]
    repo.tag(1, "test", remove=True)
    snippet = repo.get(1)
    assert snippet is not None
    assert snippet.tag_list == ["test2"]
    repo.tag(1, "test3", "test4", "test2")
    snippet = repo.get(1)
    # default sort and no duplicates
    assert snippet is not None
    assert snippet.tag_list == ["test2", "test3", "test4"]
    repo.tag(1, "test2", "test3", "test3", remove=True)
    snippet = repo.get(1)
    # removed both tags even if specified twice
    assert snippet is not None
    assert snippet.tag_list == ["test4"]
    with pytest.raises(SnippetNotFoundError):
        repo.tag(100, "test")


def test_tag_raises_value_error_if_remove_and_no_tags():
    repo = InMemorySnippetRepo()
    snippet = Snippet.create_snippet(
        title="Empty Tag Test",
        code="print('hello')",
        language=Language.PYTHON,
    )
    repo.add(snippet)
    with pytest.raises(ValueError, match="No tags provided to remove."):
        repo.tag(snippet.id, remove=True)  # type: ignore


def test_json_get_raises_if_snippet_not_found():
    with tempfile.TemporaryDirectory() as tempdir:
        json_file = Path(tempfile.mktemp(suffix=".json", dir=tempdir))

        # Inicializamos el archivo con un snippet de ID distinto
        json_file.write_text(
            json.dumps(
                [
                    {
                        "id": 1,
                        "title": "Test",
                        "code": "print(1)",
                        "language": "python",
                        "tags": "",
                        "favorite": False,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                    }
                ]
            ),
            encoding="utf-8",
        )

        repo = JSONSnippetRepo(json_file)

        # Buscar un ID que no existe
        with pytest.raises(
            SnippetNotFoundError, match="Snippet with ID 999 not found."
        ):
            repo.get(999)
