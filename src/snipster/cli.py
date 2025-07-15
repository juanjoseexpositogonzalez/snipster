import asyncio
from typing import Any, Dict, Final

import httpx
import typer
from carbon.carbon import create_code_image
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
PISTON_API: Final[str] = "https://emkc.org/api/v2/piston/execute"
GITHUB_TOKEN: Final[str] = config("GITHUB_TOKEN", default="")  # type: ignore[assignment]


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
    language: Language = typer.Option(Language.PYTHON, "--language", "--lang", "-l"),
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
    sort: bool = typer.Option(False, "--sort", "-s", help="Sort tags alphabetically"),
):
    repo: DBSnippetRepo = ctx.obj
    try:
        # repo.get(snippet_id)
        repo.tag(snippet_id, tag, remove=remove, sort=sort)
        action = "removed from" if remove else "added to"
        console.print(
            f"[bold green]Tag '{tag}' {action} snippet {snippet_id}[/bold green]."
        )
    except SnippetNotFoundError:
        console.print(f"[bold red]Snippet {snippet_id} not found[/bold red].")


@app.command(name="run")
def run_code(
    ctx: typer.Context,
    snippet_id: int = typer.Argument(..., help="Snippet ID to run"),
    version: str = typer.Option(
        "3.10.0", "--version", "-v", help="Language version to use"
    ),
) -> Dict[str, Any]:
    """
    Run code in a specific language using Piston API.
    """
    try:
        result = asyncio.run(_run_code_async(ctx, snippet_id, version))
    except httpx.HTTPError as e:
        console.print(f"[bold red]HTTPError: {e}[/bold red]")
        raise typer.Exit(code=1)

    if result:
        console.print("[bold green]Execution completed![/bold green]")

        if result["stdout"]:
            console.print("[bold blue]STDOUT:[/bold blue]")
            console.print(result["stdout"])

        if result["stderr"]:
            console.print("[bold red]STDERR:[/bold red]")
            console.print(result["stderr"])

        if result["output"]:
            console.print("[bold yellow]OUTPUT:[/bold yellow]")
            console.print(result["output"])

    return result


async def _run_code_async(
    ctx: typer.Context,
    snippet_id: int,
    version: str = "3.10.0",  # Default to latest version
) -> Dict[str, Any]:
    repo: DBSnippetRepo = ctx.obj
    try:
        snippet = repo.get(snippet_id)
    except SnippetNotFoundError:
        console.print(f"[bold red]Snippet with id {snippet_id} not found[/bold red].")
        return {}

    payload: Dict[str, Any] = {
        "language": snippet.language.value,
        "version": version,
        "files": [{"content": snippet.code}],
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(PISTON_API, json=payload)
        if response.status_code != 200:
            raise httpx.HTTPError("Code execution failed")

        result = response.json()

        stdout = result.get("run", {}).get("stdout", "")
        stderr = result.get("run", {}).get("stderr", "")
        output = result.get("run", {}).get("output", "")

        return {"stdout": stdout, "stderr": stderr, "output": output}


@app.command()
def image(
    ctx: typer.Context,
    snippet_id: int = typer.Argument(..., help="Snippet ID to get image"),
):
    repo: DBSnippetRepo = ctx.obj

    snippet = repo.get(snippet_id)
    if not snippet:
        console.print(f"[bold red]Snippet with id {snippet_id} not found[/bold red].")
        return
    create_code_image(
        code=snippet.code,
        language=snippet.language.value,
        theme="seti",
        line_numbers="false",
        background="#ABB8C3",
        wt="sharp",
        destination=".",  # type: ignore[assignment]
    )
    console.print(
        f"[bold blue]Image for snippet '{snippet.title}' created successfully![/bold blue]"
    )


@app.command()
def gist(
    ctx: typer.Context,
    snippet_id: int = typer.Argument(..., help="Snippet ID to crate gist for"),
    public: bool = typer.Option(True, "--public", "-p", help="Create public Gist"),
):
    """
    Create a Gist from a snippet.
    """
    repo: DBSnippetRepo = ctx.obj
    try:
        # Check if snippet exists
        snippet = repo.get(snippet_id)
    except SnippetNotFoundError:
        console.print(f"[bold red]Snippet with id {snippet_id} not found[/bold red].")
        return

    # Here you would implement the logic to create a Gist using GitHub API
    # For now, we will just print a message
    url = create_gist(snippet.code, snippet.title, public)
    console.print(
        f"[bold green]Gist for snippet '{snippet.title}' created successfully!\nSee url: {url}[/bold green]"
    )


def create_gist(code: str, title: str, public: bool = False) -> str:
    """Create a GitHub Gist and return its URL.

    Args:
        title: The title/filename for the gist
        code: The code content
        public: Whether the gist should be public (default: False for private)

    Returns:
        str: The URL of the created gist

    Raises:
        Exception: If gist creation fails
    """
    # Prepare the gist data
    gist_data: Dict[str, Any] = {
        "description": f"Code snippet: {title}",
        "public": public,
        "files": {
            f"{title}.py": {  # You might want to determine extension based on language
                "content": code
            }
        },
    }

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }

    try:
        # Make the request to GitHub API
        response = httpx.post(
            "https://api.github.com/gists", json=gist_data, headers=headers, timeout=30
        )

        # Check if request was successful
        if response.status_code == 201:
            gist_info = response.json()
            return gist_info["html_url"]

        # Handle different error cases
        elif response.status_code == 401:
            raise httpx.HTTPStatusError(
                response=response,
                request=response.request,
                message="GitHub token is invalid or expired",
            )
        elif response.status_code == 403:
            raise httpx.HTTPStatusError(
                response=response,
                request=response.request,
                message="GitHub API rate limit exceeded or forbidden",
            )
        elif response.status_code == 422:
            error_detail = response.json().get("message", "Invalid request data")
            raise httpx.HTTPStatusError(
                response=response,
                request=response.request,
                message=f"Invalid gist data: {error_detail}",
            )
        else:
            error_detail = response.json().get("message", "Unknown error")
            raise httpx.HTTPError(
                f"GitHub API error ({response.status_code}): {error_detail}"
            )

    except httpx.HTTPStatusError as e:
        raise httpx.HTTPError(f"Network error when creating gist: {str(e)}") from e
    except KeyError as e:
        raise httpx.HTTPError(
            f"Unexpected response format from GitHub API: missing {str(e)}"
        ) from e
