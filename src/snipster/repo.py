import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, Sequence

from decouple import config
from sqlmodel import Session, select

from .exceptions import SnippetNotFoundError
from .models import Snippet


class SnippetRepository(ABC):  # pragma: no cover
    @abstractmethod
    def add(self, snippet: Snippet) -> None:
        """Add a new snippet to the repository."""

    @abstractmethod
    def list(self) -> Sequence[Snippet]:
        """List all snippets in the repository."""

    @abstractmethod
    def get(self, snippet_id: int) -> Snippet | None:
        """Get a snippet by its ID.

        Args:
            snippet_id (int): The ID of the snippet to retrieve.

        Raises:
            SnippetNotFoundError: If the snippet with the given ID does not exist.

        Returns:
            Snippet: The snippet with the specified ID.
        """

    @abstractmethod
    def delete(self, snippet_id: int) -> None:  # type: ignore
        """Delete a snippet by its ID.

        Args:
            snippet_id (int): The ID of the snippet to delete.

        Raises:
            SnippetNotFoundError: If the snippet with the given ID does not exist.
        """


class InMemorySnippetRepo(SnippetRepository):
    def __init__(self):
        self.snippets: Dict[int, Snippet] = {}

    def add(self, snippet: Snippet) -> None:
        next_id = max(self.snippets.keys(), default=0) + 1
        snippet.id = next_id  # type: ignore
        self.snippets[snippet.id] = snippet  # type: ignore

    def list(self) -> Sequence[Snippet]:
        return list(self.snippets.values())

    def get(self, snippet_id: int) -> Snippet | None:
        return self.snippets.get(snippet_id, None)

    def delete(self, snippet_id: int) -> None:
        if snippet_id not in self.snippets:
            raise SnippetNotFoundError(f"Snippet with ID {snippet_id} not found.")
        self.snippets.pop(snippet_id, None)  # type: ignore


class DBSnippetRepo(SnippetRepository):
    """A repository that uses a database to store snippets."""

    def __init__(self, session: Session):
        """Initialize the repository with an optional SQLModel session."""
        self.session = session

    def add(self, snippet: Snippet) -> None:
        self.session.add(snippet)
        self.session.commit()
        self.session.refresh(snippet)

    def list(self) -> Sequence[Snippet]:
        """List all snippets in the database."""
        return self.session.exec(select(Snippet)).all()

    def get(self, snippet_id: int) -> Snippet:
        """Get a snippet by its ID."""

        snippet = self.session.get(Snippet, snippet_id)
        if snippet is None:
            raise SnippetNotFoundError(f"Snippet with ID {snippet_id} not found.")
        return snippet

    def delete(self, snippet_id: int) -> None:
        """Delete a snippet by its ID."""

        snippet = self.session.get(Snippet, snippet_id)
        if snippet is None:
            raise SnippetNotFoundError(f"Snippet with ID {snippet_id} not found.")
        self.session.delete(snippet)
        self.session.commit()


class DateTimeEncoder(json.JSONEncoder):
    """JSONEncoder que convierte datetime a ISO 8601 automáticamente."""

    def default(self, o: object) -> str:
        if isinstance(o, datetime):
            return o.isoformat()
        # Dejar que el encoder base maneje el resto de casos
        return super().default(o)


class JSONSnippetRepo(SnippetRepository):
    """A repository that uses a JSON file to store snippets."""

    def __init__(self, file_path: Path):
        """Initialize the repository with a file path."""
        self.file_path = file_path
        # self.snippets: Sequence[Snippet] = self._load_snippets(file_path)

    def _load_snippets(self, file_path: Path) -> Sequence[Snippet]:
        """Load snippets from a JSON file."""
        if not file_path.exists() or len(file_path.read_text()) == 0:
            return []
        with file_path.open("r") as f:
            return [Snippet(**data) for data in json.load(f)]

    def _save_snippets(self, file_path: Path, snippets: Sequence[Snippet]) -> None:
        """Save snippets to a JSON file."""
        with file_path.open("w") as f:
            json.dump(
                [snippet for snippet in snippets],
                f,
                indent=2,
                cls=DateTimeEncoder,
            )

    def add(self, snippet: Snippet) -> None:
        file_path = Path(config("SNIPPET_JSON_FILE", default="snippets.json"))  # type: ignore

        if snippet.id is None:
            # Assign a new ID based on the current number of snippets
            snippets = self._load_snippets(file_path)
            last_id = max((s.id for s in snippets), default=0)  # type: ignore
            snippet.id = last_id + 1
        else:
            snippets = self._load_snippets(file_path)

        snippets.append(snippet.model_dump())  # type: ignore
        self._save_snippets(file_path, snippets)

    def list(self) -> Sequence[Snippet]:
        file_path = Path(config("SNIPPET_JSON_FILE", default="snippets.json"))  # type: ignore
        return self._load_snippets(file_path)

    def get(self, snippet_id: int) -> Snippet:
        file_path = Path(config("SNIPPET_JSON_FILE", default="snippets.json"))  # type: ignore
        snippets = self._load_snippets(file_path)
        for snippet in snippets:
            if snippet.id == snippet_id:
                return snippet
        raise SnippetNotFoundError(f"Snippet with ID {snippet_id} not found.")

    def delete(self, snippet_id: int) -> None:
        file_path = Path(config("SNIPPET_JSON_FILE", default="snippets.json"))  # type: ignore
        snippets = self._load_snippets(file_path)
        for i, snippet in enumerate(snippets):
            if snippet.id == snippet_id:
                del snippets[i]  # type: ignore
                self._save_snippets(file_path, snippets)
                return
        raise SnippetNotFoundError(f"Snippet with ID {snippet_id} not found.")
