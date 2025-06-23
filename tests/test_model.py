import pytest
from sqlmodel import Session, SQLModel, create_engine

from src.snipster.models import Language, Snippet

engine = create_engine("sqlite:///:memory:", echo=False)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


def test_create_snippet():
    snippet = Snippet(
        title="Test Snippet",
        code="print('Hello, World!')",
        language=Language.PYTHON,
        description="A simple hello world snippet",
        tags="test,example",
    )

    with Session(engine) as session:
        session.add(snippet)
        session.commit()
        session.refresh(snippet)

        assert snippet.id is not None
        assert snippet.title == "Test Snippet"
        assert snippet.language == Language.PYTHON
        assert snippet.description == "A simple hello world snippet"
        assert snippet.tags == "test,example"


def test_create_snippet_with_cls_method():
    snippet = {
        "title": "Test Snippet with Class Method",
        "code": "print('Hello, Class Method!')",
        "language": Language.JAVASCRIPT,
        "description": "A simple hello world snippet using class method",
        "tags": "test,example",
    }

    snippet_instance = Snippet.create(**snippet)
    with Session(engine) as session:
        session.add(snippet_instance)
        session.commit()
        session.refresh(snippet_instance)

        assert snippet_instance.id is not None
        assert snippet_instance.title == "Test Snippet with Class Method"
        assert snippet_instance.language == Language.JAVASCRIPT
        assert (
            snippet_instance.description
            == "A simple hello world snippet using class method"
        )
        assert snippet_instance.tags == "test,example"
