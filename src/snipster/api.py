"""API endpoints for Snipster application."""

from typing import Annotated, Dict, List

import httpx
from carbon.carbon import create_code_image
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Session, SQLModel, create_engine

from snipster.cli import PISTON_API
from snipster.exceptions import SnippetNotFoundError

from .cli import create_gist
from .models import Language, Snippet, SnippetCreate
from .repo import DBSnippetRepo, SnippetRepository

app = FastAPI()


def get_repo() -> SnippetRepository:
    """Dependency to get the snippet repository."""
    database_url = "sqlite:///snipster.db"
    engine = create_engine(database_url, echo=True)
    SQLModel.metadata.create_all(engine)
    return DBSnippetRepo(Session(engine))


@app.post("/snippets/", response_model=Snippet)  # type: ignore
def create_snippet(
    snippet: SnippetCreate,
    repo: Annotated[SnippetRepository, Depends(get_repo)],
) -> Snippet:
    """Add a new snippet."""
    try:
        snippet = Snippet.create_snippet(**snippet.model_dump())  # type: ignore
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    repo.add(snippet)  # type: ignore
    return snippet  # type: ignore


@app.get("/snippets/", response_model=list[Snippet])  # type: ignore
def read_snippets(
    repo: Annotated[SnippetRepository, Depends(get_repo)],
) -> list[Snippet]:
    """List all snippets."""
    snippets = repo.list()
    if not snippets:
        raise HTTPException(status_code=404, detail="No snippets found")
    return snippets  # type: ignore


@app.get("/snippets/{snippet_id}", response_model=Snippet)  # type: ignore
def read_snippet(
    snippet_id: int,
    repo: Annotated[SnippetRepository, Depends(get_repo)],
) -> Snippet:
    """Get a snippet by ID."""
    snippet = repo.get(snippet_id)
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")
    return snippet


@app.delete("/snippets/{snippet_id}")  # type: ignore
def delete_snippet(
    snippet_id: int,
    repo: Annotated[SnippetRepository, Depends(get_repo)],
) -> Dict[str, str]:
    """Delete a snippet by ID."""
    snippet = repo.get(snippet_id)
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")
    repo.delete(snippet.id)  # type: ignore
    return {"message": f"Snippet with ID {snippet_id} deleted successfully."}  # type: ignore


@app.post("/snippets/{snippet_id}/favorite")  # type: ignore
def favorite_snippet(
    snippet_id: int,
    repo: Annotated[SnippetRepository, Depends(get_repo)],
) -> Dict[str, str]:
    """Mark a snippet as favorite."""
    snippet = repo.get(snippet_id)
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")
    repo.toggle_favorite(snippet_id)
    snippet = repo.get(snippet_id)
    return {"message": f"Snippet with ID {snippet_id} favorited"}  # type: ignore


@app.get("/snippets/search/", response_model=list[Snippet])  # type: ignore
def search_snippets(
    repo: Annotated[SnippetRepository, Depends(get_repo)],
    term: str = Query(...),
    language: Language | None = Query(None, description="Filter by language"),
) -> list[Snippet]:
    """Search snippets by title or code."""
    snippets = repo.search(term, language=language)
    if not snippets:
        raise HTTPException(status_code=404, detail="No snippets found")
    return snippets  # type: ignore


@app.post("/snippets/{snippet_id}/tags")  # type: ignore
def tag_snippet(
    repo: Annotated[SnippetRepository, Depends(get_repo)],
    snippet_id: int,
    tags: List[str] = Query(..., description="Tags to add to the snippet"),
    remove: bool = Query(False, description="Remove tags instead of adding"),
    sort: bool = Query(False, description="Sort tags alphabetically"),
) -> Dict[str, str]:
    """Add a tag to a snippet."""
    snippet = repo.get(snippet_id)
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")
    repo.tag(snippet_id, *tags, remove=remove, sort=sort)  # type: ignore
    return {
        "message": f"Tag '{tags}' {'removed from' if remove else 'added to'} snippet {snippet_id}."
    }


@app.post("/snippets/{snippet_id}/run")  # type: ignore
async def run_snippet(
    repo: Annotated[SnippetRepository, Depends(get_repo)],
    snippet_id: int,
    version: str = Query("3.10.0", description="Version of the snippet to run"),
) -> Dict[str, str]:
    """Run a code snippet."""

    try:
        snippet: Snippet | None = repo.get(snippet_id)

        payload: Dict[str, str] = {
            "language": snippet.language.value,  # type: ignore
            "version": version,
            "files": [{"content": snippet.code}],  # type: ignore
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(PISTON_API, json=payload)
            if response.status_code != 200:
                raise httpx.HTTPError(
                    f"Error running snippet: {response.text}",
                )
            result = response.json()

        if "run" not in result or "stdout" not in result["run"]:
            raise HTTPException(
                status_code=500,
                detail="Unexpected response format from Piston API",
            )
        return {
            "stdout": result.get("run", {}).get("stdout", ""),
            "stderr": result.get("run", {}).get("stderr", ""),
            "output": result.get("run", {}).get("output", ""),
        }

    except SnippetNotFoundError as exc:
        return {"error": str(exc)}


@app.post("/snippets/{snippet_id}/image")  # type: ignore
def create_snippet_image(
    repo: Annotated[SnippetRepository, Depends(get_repo)], snippet_id: int
):
    """Create an image from a code snippet."""
    snippet = repo.get(snippet_id)
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")

    try:
        create_code_image(
            code=snippet.code,
            language=snippet.language.value,
            theme="seti",
            line_numbers="false",
            background="#ABB8C3",
            wt="sharp",
            destination=".",  # type: ignore[assignment]
        )
        return {"message": f"Image for snippet '{snippet.title}' created successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/snippets/{snippet_id}/gist")  # type: ignore
def create_snippet_gist(
    repo: Annotated[SnippetRepository, Depends(get_repo)],
    snippet_id: int,
    public: bool = Query(False, description="Create a public Gist"),
):
    """Create a Gist from a snippet."""
    snippet = repo.get(snippet_id)
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")

    try:
        gist_url = create_gist(
            title=snippet.title,
            code=snippet.code,
            public=public,
        )
        return {"message": f"Gist created successfully: {gist_url}"}
    except HTTPException as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
