"""Title endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_titles() -> dict[str, str]:
    """List all US Code titles."""
    return {"message": "List of titles - not yet implemented"}


@router.get("/{title_number}")
async def get_title(title_number: int) -> dict[str, str]:
    """Get a specific title by number."""
    return {"message": f"Title {title_number} - not yet implemented"}
