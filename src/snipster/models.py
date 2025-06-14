from datetime import datetime
from enum import StrEnum
from typing import Optional

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


engine = create_engine(f"sqlite:///{config("DATABASE_NAME")}", echo=False)


class Snippet(SQLModel, table=True):
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

    @classmethod
    def create(cls, **kwargs) -> "Snippet":
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


if __name__ == "__main__":
    SQLModel.metadata.create_all(engine)
    print("Database and tables created successfully.")
