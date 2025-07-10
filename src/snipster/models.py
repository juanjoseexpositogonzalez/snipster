from datetime import datetime
from enum import StrEnum
from typing import Any, Optional, Self, Sequence

from decouple import config
from sqlmodel import Field, SQLModel, create_engine


class Language(StrEnum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    C_SHARP = "c#"
    C_PLUS_PLUS = "c++"
    RUBY = "ruby"
    PHP = "php"
    GO = "go"
    SWIFT = "swift"
    KOTLIN = "kotlin"
    TYPESCRIPT = "typescript"
    RUST = "rust"
    HTML = "html"
    CSS = "css"


class Snippet(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    code: str
    description: Optional[str] = Field(default=None)
    language: Language
    tags: Optional[str] = Field(default=None)  # Using a list to store tags
    created_at: Optional[datetime] = Field(
        default=datetime.now()
    )  # Use a string for simplicity, could be datetime
    updated_at: Optional[datetime] = Field(default=datetime.now())
    favorite: bool = Field(default=False)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

    def __str__(self) -> str:
        """Return a string representation of the Snippet instance."""
        return f"Snippet(id={self.id}, title={self.title}, language={self.language}, created_at={self.created_at})"

    @property
    def tag_list(self) -> Sequence[str]:
        """Return a list of tags associated with the snippet."""
        return self.tags.split(",") if self.tags else []  # type: ignore

    @classmethod
    def create(cls, **kwargs: Any) -> Self:
        """Create a new Snippet instance with the current timestamp for created_at and updated_at.
        Args:
            **kwargs: Keyword arguments to initialize the Snippet instance.
        Returns:
            Snippet: A new Snippet instance with created_at and updated_at set to the current time.
        """

        snippet = cls(**kwargs)
        snippet.updated_at = datetime.now()
        snippet.created_at = datetime.now()
        return snippet

    @classmethod
    def create_snippet(
        cls,
        title: str,
        code: str,
        language: Language,
        description: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> "Snippet":
        """Create a new Snippet instance with the provided parameters.

        Args:
            title (str): The title of the snippet.
            code (str): The code content of the snippet.
            language (Language): The programming language of the snippet.
            description (Optional[str]): A description of the snippet.
            tags (Optional[str]): Tags associated with the snippet.

        Returns:
            Snippet: A new Snippet instance.
        """
        if len(title) < 3:
            raise ValueError("Title must be at least 3 characters long.")
        return cls.create(
            title=title,
            code=code,
            language=language,
            description=description,
            tags=tags,
        )


if __name__ == "__main__":  # pragma: no cover
    # Create the database and tablesprint("Database and tables created successfully.")
    database_url = config("DATABASE_URL", default="sqlite:///snippets.db")
    engine = create_engine(database_url, echo=True)  # type: ignore
    SQLModel.metadata.create_all(engine)
    print("Database and tables created successfully.")
