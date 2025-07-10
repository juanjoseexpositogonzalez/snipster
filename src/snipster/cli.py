import typer
from decouple import config
from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from sqlmodel import Session, SQLModel, create_engine

from snipster.exceptions import SnippetNotFoundError
from snipster.models import Language, Snippet
from snipster.repo import DBSnippetRepo

app = typer.Typer()
console = Console()


@app.callback()
def init(ctx: typer.Context) -> None:
    """
    Snipster CLI - A command-line interface for managing your snippets.
    """
    database_url = config("DATABASE_URL", default="sqlite:///snippets.db")
    engine = create_engine(
        database_url,  # type: ignore[assignment]
        echo=False,
    )

    SQLModel.metadata.create_all(engine)
    ctx.obj = DBSnippetRepo(Session(engine))


@app.command()
def add(
    ctx: typer.Context,
    title: str = typer.Argument(...),
    code: str = typer.Argument(...),
    language: Language = typer.Option(Language.PYTHON, "--language", "--lang"),
    description: str = typer.Option(
        None, "--description", "-desc", help="Snippet description"
    ),
    tag: str = typer.Option(None, "--tag", "-t", help="Tag for the snippet"),
):
    repo: DBSnippetRepo = ctx.obj
    snippet = Snippet.create_snippet(
        title=title, code=code, language=language, description=description, tags=tag
    )
    repo.add(snippet)
    console.print(f"[bold green]Snippet '{snippet.title}' added[/bold green].")


@app.command(name="list")
def list_snippets(ctx: typer.Context):
    repo: DBSnippetRepo = ctx.obj
    snippets = repo.list()

    if not snippets:
        console.print("[bold yellow]No snippets found.[/bold yellow]")
    for snippet in snippets:
        # typer.echo(f"{snippet.id}: {snippet.title} ({snippet.language})")
        # console.print(
        #     f"[bold blue]{snippet.id}[/bold blue]: {snippet.title} [dim]({snippet.language})[/dim]"
        # )
        description_text = Text(
            snippet.description if snippet.description else "No description",
            style="gray50",
        )
        empty_line = Text("")  # Línea en blanco
        code_block = Syntax(
            snippet.code,
            snippet.language,
            theme="monokai",
            line_numbers=False,
            background_color="gray50",
        )
        tags_text = Text(
            f"Tags: {', '.join(snippet.tag_list)}" if snippet.tags else "Tags:",
            style="gray50",
        )

        # Usamos Group para combinar todos los renderizables
        group = Group(description_text, empty_line, code_block, empty_line, tags_text)

        # ⭐ Añadir estrella si es favorito
        title_prefix = "⭐ " if snippet.favorite else ""
        panel_title = (
            f"{title_prefix}[bold cyan]1: {snippet.title} [green]{snippet.language}[/]"
        )

        # Creamos el panel
        panel = Panel.fit(
            group,
            title=panel_title,
            border_style="cyan",
        )

        console.print(panel)


@app.command()
def delete(ctx: typer.Context, snippet_id: int = typer.Argument(...)):
    repo: DBSnippetRepo = ctx.obj

    # Verificar si existe sin lanzar excepción
    snippets = repo.list()
    snippet_exists = any(s.id == snippet_id for s in snippets)

    if not snippet_exists:
        console.print(f"[bold red]Snippet with id {snippet_id} not found.[/bold red]")
        return

    repo.delete(snippet_id)
    rich_text = Text(f"Snippet {snippet_id} deleted.", style="bold green")
    console.print(rich_text)


@app.command()
def search(ctx: typer.Context, query: str = typer.Argument(..., help="Search query")):
    repo: DBSnippetRepo = ctx.obj
    snippets = repo.search(query)
    if not snippets:
        # typer.echo("No snippets found.")
        console.print("[bold red]Snippets not found.[/bold red]")
    else:
        for snippet in snippets:
            # typer.echo(f"{snippet.id}: {snippet.title} ({snippet.language})")
            console.print(
                f"[bold blue]{snippet.id}: {snippet.title} ({snippet.language})[/]"
            )


@app.command(name="toggle-favorite")
def toggle_favorite(ctx: typer.Context, snippet_id: int = typer.Argument(...)):
    repo: DBSnippetRepo = ctx.obj
    try:
        snippet = repo.get(snippet_id)
        old_status = snippet.favorite
        repo.toggle_favorite(snippet_id)
        new_status = not old_status
        status = "favorited" if new_status else "unfavorited"
        console.print(
            f"[bold green]Snippet {snippet_id} has been {status}[/bold green]."
        )
    except SnippetNotFoundError:
        console.print(f"[bold red]Snippet {snippet_id} not found[/bold red].")


@app.command()
def tag(
    ctx: typer.Context,
    snippet_id: int = typer.Argument(..., help=""),
    tag: str = typer.Argument(..., help="Tag to add or remove"),
    remove: bool = typer.Option(False, "--remove", "-r", help="Remove tags"),
):
    repo: DBSnippetRepo = ctx.obj
    try:
        # repo.get(snippet_id)
        repo.tag(snippet_id, tag, remove=remove)
        action = "removed from" if remove else "added to"
        console.print(
            f"[bold green]Tag '{tag}' {action} snippet {snippet_id}[/bold green]."
        )
    except SnippetNotFoundError:
        console.print(f"[bold red]Snippet {snippet_id} not found[/bold red].")
