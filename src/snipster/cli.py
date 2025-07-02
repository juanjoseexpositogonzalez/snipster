import typer
from sqlmodel import Session, create_engine

from snipster.models import Language, Snippet
from snipster.repo import DBSnippetRepo

app = typer.Typer()


@app.callback()
def init(ctx: typer.Context):
    """
    Snipster CLI - A command-line interface for managing your snippets.
    """
    engine = create_engine(
        f"sqlite:///{typer.get_app_dir('snipster')}/snippets.db", echo=False
    )
    ctx.obj = DBSnippetRepo(Session(engine))


@app.command()
def add(title: str, code: str, language: Language, ctx: typer.Context):
    repo: DBSnippetRepo = ctx.obj
    snippet = Snippet.create_snippet(title=title, code=code, language=language)
    repo.add(snippet)


if __name__ == "__main__":
    app()
