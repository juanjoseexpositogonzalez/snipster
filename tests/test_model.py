import datetime

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
        created_at=None,
        updated_at=None,
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
        assert isinstance(snippet.created_at, datetime.datetime)
        assert isinstance(snippet.updated_at, datetime.datetime)
        assert abs((snippet.updated_at - snippet.created_at).total_seconds()) < 1


def test_snippet_assigns_now_when_created_at_is_none(mocker):  # type: ignore
    mock_now = mocker.patch("src.snipster.models.datetime")
    mock_now.now.return_value = datetime.datetime(2024, 1, 1)

    snippet = Snippet(
        title="test",
        code="print('hi')",
        language=Language.PYTHON,
        created_at=None,
        updated_at=None,
    )

    assert snippet.created_at == datetime.datetime(2024, 1, 1)
    assert snippet.updated_at == datetime.datetime(2024, 1, 1)


def test_create_snippet_with_short_title_raises_value_error():
    with pytest.raises(ValueError) as excinfo:
        Snippet.create_snippet(
            title="Hi",  # menos de 3 caracteres
            code="print('Hello')",
            language=Language.PYTHON,
        )

    assert str(excinfo.value) == "Title must be at least 3 characters long."


def test_create_snippet_valid_title():
    snippet = Snippet.create_snippet(
        title="Valid Title",
        code="print('Hello')",
        language=Language.PYTHON,
        description="Demo snippet",
        tags="example, test",
    )

    assert snippet.title == "Valid Title"
    assert snippet.code == "print('Hello')"
    assert snippet.language == Language.PYTHON
    assert snippet.description == "Demo snippet"
    assert snippet.tags == "example, test"


def test_create_snippet_with_cls_method():
    """Test creating a snippet using the class method."""
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
