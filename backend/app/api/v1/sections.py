"""Section endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/{title_number}/{section_number}")
async def get_section(title_number: int, section_number: str) -> dict[str, str]:
    """Get a specific section."""
    return {
        "message": f"Section {title_number} USC § {section_number} - not yet implemented"
    }


@router.get("/{title_number}/{section_number}/blame")
async def get_section_blame(title_number: int, section_number: str) -> dict[str, str]:
    """Get blame view for a section."""
    return {
        "message": f"Blame for {title_number} USC § {section_number} - not yet implemented"
    }
