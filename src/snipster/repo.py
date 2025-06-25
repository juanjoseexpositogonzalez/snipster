import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, Sequence

from sqlmodel import Session, select

from .exceptions import SnippetNotFoundError
from .models import Snippet


class SnippetRepository(ABC):  # pragma: no cover
    """Abstract base class for snippet repositories."""

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

        Raises (future):
            SnippetNotFoundError: If the snippet with the given ID does not exist.

        Returns:
            Snippet: The snippet with the given ID or None if not found.
        """

    @abstractmethod
    def delete(self, snippet_id: int) -> None:  # type: ignore
        """Delete a snippet by its ID.

        Args:
            snippet_id (int): The ID of the snippet to delete.

        Raises:
            SnippetNotFoundError: If the snippet with the given ID does not exist.
        """

    @abstractmethod
    def search(self, term: str, *, language: str | None = None) -> Sequence[Snippet]:
        """Search for snippets by term and optional language.

        Args:
            term (str): The search term.
            language (str | None): Optional language filter.

        Returns:
            Sequence[Snippet]: A sequence of snippets matching the search criteria.
        """

    @abstractmethod
    def toggle_favorite(self, snippet_id: int) -> None:
        """Toggle the favorite status of a snippet.

        Args:
            snippet_id (int): The ID of the snippet to toggle.

        Returns:
            Snippet: The updated snippet with the new favorite status.

        Raises:
            SnippetNotFoundError: If the snippet with the given ID does not exist.
        """

    @abstractmethod
    def tag(
        self, snippet_id: int, /, *tags: str, remove: bool = False, sort: bool = True
    ) -> None:
        """Add or remove tags from a snippet.

        Args:
            snippet_id (int): The ID of the snippet to tag.
            *tags (str): Tags to add or remove.
            remove (bool): If True, remove the tags instead of adding them.
            sort (bool): If True, sort the tags after adding/removing.

        Raises:
            SnippetNotFoundError: If the snippet with the given ID does not exist.
        """

    def _update_tags(
        self, snippet: Snippet, tags: Sequence[str], *, remove: bool, sort: bool = True
    ) -> str:
        """Update the tags of a snippet.

        Args:
            snippet_id (int): The ID of the snippet to update.
            tags (Sequence[str]): The new tags to set for the snippet.
            sort (bool): If True, sort the tags after updating.

        Raises:
            SnippetNotFoundError: If the snippet with the given ID does not exist.

        Returns:
            str: The updated tags as a comma-separated string.
        """

        if snippet.tags is None:
            snippet.tags = ""

        existing = list(snippet.tag_list)
        existing.extend(tags)
        existing = list(set(existing))  # Remove duplicates

        if remove:
            for tag in tags:
                tag = tag.strip()
                if tag in existing:
                    existing.remove(tag)

        existing = sorted(existing) if sort else existing

        return ",".join(existing) if existing else ""  # type: ignore


class InMemorySnippetRepo(SnippetRepository):
    def __init__(self):
        self.snippets: Dict[int, Snippet] = {}

    def add(self, snippet: Snippet) -> None:
        """Add a new snippet to the repository."""
        next_id = max(self.snippets.keys(), default=0) + 1
        snippet.id = next_id  # type: ignore
        self.snippets[snippet.id] = snippet  # type: ignore

    def list(self) -> Sequence[Snippet]:
        return list(self.snippets.values())

    def get(self, snippet_id: int) -> Snippet | None:
        if snippet_id not in self.snippets:
            return None
            # raise SnippetNotFoundError(f"Snippet with ID {snippet_id} not found.")
        return self.snippets.get(snippet_id)  # type: ignore

    def delete(self, snippet_id: int) -> None:
        if snippet_id not in self.snippets:
            raise SnippetNotFoundError(f"Snippet with ID {snippet_id} not found.")
        self.snippets.pop(snippet_id, None)  # type: ignore

    def search(self, term: str, *, language: str | None = None) -> Sequence[Snippet]:
        """Search for snippets by term and optional language."""
        results = []
        for snippet in self.snippets.values():
            if term.lower() in str(snippet).lower():
                if language is None or snippet.language == language:
                    results.append(snippet)
        return results

    def toggle_favorite(self, snippet_id: int) -> None:
        """Toggle the favorite status of a snippet.

        Args:
            snippet_id (int): The ID of the snippet to toggle.

        Returns:
            Snippet: The updated snippet with the new favorite status.

        Raises:
            SnippetNotFoundError: If the snippet with the given ID does not exist.
        """
        if snippet_id not in self.snippets:
            raise SnippetNotFoundError(f"Snippet with ID {snippet_id} not found.")
        snippet = self.snippets[snippet_id]
        snippet.favorite = not snippet.favorite  # type: ignore
        self.snippets[snippet_id] = snippet

    def tag(
        self, snippet_id: int, /, *tags: str, remove: bool = False, sort: bool = True
    ) -> None:
        """Add or remove tags from a snippet.

        Args:
            snippet_id (int): The ID of the snippet to tag.
            *tags (str): Tags to add or remove.
            remove (bool): If True, remove the tags instead of adding them.
            sort (bool): If True, sort the tags after adding/removing.

        Raises:
            SnippetNotFoundError: If the snippet with the given ID does not exist.
            ValueError: If no tags are provided to remove.
        """
        snippet = self.get(snippet_id)  # Raises SnippetNotFoundError if not found
        if remove and not tags:
            raise ValueError("No tags provided to remove.")
        if snippet is None:
            raise SnippetNotFoundError(f"Snippet with ID {snippet_id} not found.")
        snippet.tags = self._update_tags(snippet, tags, remove=remove, sort=sort)
        self.snippets[snippet_id] = snippet  # type: ignore


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

    def search(self, term: str, *, language: str | None = None) -> Sequence[Snippet]:
        """Search for snippets by term and optional language.

        Args:
            term (str): The search term.
            language (str | None): Optional language filter.

        Returns:
            Sequence[Snippet]: A sequence of snippets matching the search criteria.
        """
        snippets: Sequence[Snippet] = []
        statement = select(Snippet)
        results = self.session.exec(statement)
        for snippet in results:
            if (
                term.lower() in snippet.title.lower()
                or term.lower() in snippet.code.lower()
            ):
                if language is None or snippet.language == language:
                    snippets.append(snippet)

        return snippets

    def toggle_favorite(self, snippet_id: int) -> None:
        """Toggle the favorite status of a snippet.

        Args:
            snippet_id (int): The ID of the snippet to toggle.

        Returns:
            Snippet: The updated snippet with the new favorite status.

        Raises:
            SnippetNotFoundError: If the snippet with the given ID does not exist.
        """
        statement = select(Snippet).where(Snippet.id == snippet_id)
        snippet = self.session.exec(statement).first()
        if snippet is None:
            raise SnippetNotFoundError(f"Snippet with ID {snippet_id} not found.")
        snippet.favorite = not snippet.favorite  # type: ignore
        self.session.add(snippet)
        self.session.commit()
        self.session.refresh(snippet)

    def tag(
        self, snippet_id: int, /, *tags: str, remove: bool = False, sort: bool = True
    ) -> None:
        """Add or remove tags from a snippet.

        Args:
            snippet_id (int): The ID of the snippet to tag.
            *tags (str): Tags to add or remove.
            remove (bool): If True, remove the tags instead of adding them.
            sort (bool): If True, sort the tags after adding/removing.

        Raises:
            SnippetNotFoundError: If the snippet with the given ID does not exist.
        """
        statement = select(Snippet).where(Snippet.id == snippet_id)
        snippet = self.session.exec(statement).first()
        if snippet is None:
            raise SnippetNotFoundError(f"Snippet with ID {snippet_id} not found.")
        snippet.tags = self._update_tags(snippet, tags, remove=remove, sort=sort)
        self.session.add(snippet)
        self.session.commit()
        self.session.refresh(snippet)


class DateTimeEncoder(json.JSONEncoder):
    """JSONEncoder que convierte datetime a ISO 8601 automáticamente."""

    def default(self, o: object) -> str:
        if isinstance(o, datetime):
            return o.isoformat()
        # Dejar que el encoder base maneje el resto de casos
        return super().default(o)


class JSONSnippetRepo(SnippetRepository):
    """A repository that uses a JSON file to store snippets."""

    def __init__(self, path: Path):
        """Initialize the repository with a file path."""
        self.path = path
        self.path.touch(exist_ok=True)  # Ensure the file exists
        if self.path.read_text().strip() == "":
            # If the file is empty, initialize it with an empty list
            self.path.write_text("[]")
        # self.snippets: Sequence[Snippet] = self._load_snippets(file_path)

    def _load(self) -> Sequence[Snippet]:
        """Load snippets from a JSON file."""
        with self.path.open("r") as f:
            data = json.load(f)
        return [Snippet.model_validate(item) for item in data]

    def _save(self, snippets: Sequence[Snippet]) -> None:
        """Save snippets to a JSON file."""
        with self.path.open("w") as f:
            json.dump(
                [s.model_dump() for s in snippets], f, indent=2, cls=DateTimeEncoder
            )

    def add(self, snippet: Snippet) -> None:
        """Add a new snippet to the repository."""
        if snippet.id is None:
            # Assign a new ID based on the current number of snippets
            snippets = self._load()
            snippet.id = max((s.id for s in snippets), default=0) + 1  # type: ignore
            snippet.created_at = datetime.now()  # type: ignore
            snippet.updated_at = datetime.now()  # type: ignore
        else:
            snippets = self._load()

        snippets.append(snippet)  # type: ignore
        self._save(snippets)

    def list(self) -> Sequence[Snippet]:
        return self._load()

    def get(self, snippet_id: int) -> Snippet:
        """Get a snippet by its ID."""
        snippets = self._load()
        for snippet in snippets:
            if snippet.id == snippet_id:
                return snippet
        raise SnippetNotFoundError(f"Snippet with ID {snippet_id} not found.")

    def delete(self, snippet_id: int) -> None:
        snippets = self._load()
        for i, snippet in enumerate(snippets):
            if snippet.id == snippet_id:
                del snippets[i]  # type: ignore
                self._save(snippets)
                return
        raise SnippetNotFoundError(f"Snippet with ID {snippet_id} not found.")

    def search(self, term: str, *, language: str | None = None) -> Sequence[Snippet]:
        """Search for snippets by term and optional language.

        Args:
            term (str): The search term.
            language (str | None): Optional language filter.

        Returns:
            Sequence[Snippet]: A sequence of snippets matching the search criteria.
        """
        term = term.strip().lower()
        snippets = self._load()
        return [
            s
            for s in snippets
            if (term in s.title.lower() or term in s.code.lower())
            and (language is None or s.language == language)
        ]

    def toggle_favorite(self, snippet_id: int) -> None:
        """Toggle the favorite status of a snippet.

        Args:
            snippet_id (int): The ID of the snippet to toggle.

        Returns:
            Snippet: The updated snippet with the new favorite status.

        Raises:
            SnippetNotFoundError: If the snippet with the given ID does not exist.
        """
        snippets = self._load()
        snippet = next((s for s in snippets if s.id == snippet_id), None)
        if snippet is None:
            raise SnippetNotFoundError(f"Snippet with ID {snippet_id} not found.")
        snippets[snippets.index(snippet)].favorite = not snippet.favorite  # type: ignore
        self._save(snippets)

    def tag(
        self, snippet_id: int, /, *tags: str, remove: bool = False, sort: bool = True
    ) -> None:
        """Add or remove tags from a snippet.

        Args:
            snippet_id (int): The ID of the snippet to tag.
            *tags (str): Tags to add or remove.
            remove (bool): If True, remove the tags instead of adding them.
            sort (bool): If True, sort the tags after adding/removing.

        Raises:
            SnippetNotFoundError: If the snippet with the given ID does not exist.
        """
        snippets = self._load()
        snippet = next((s for s in snippets if s.id == snippet_id), None)
        if not snippet:
            raise SnippetNotFoundError(f"Snippet with ID {snippet_id} not found.")
        snippet.tags = self._update_tags(snippet, tags, remove=remove, sort=sort)
        self._save(snippets)  # type: ignore
