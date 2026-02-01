# Pydantic Schemas

This directory contains Pydantic models used for data validation and transfer between layers (pipeline, core, API).

## Naming Convention

- **`*Schema` suffix**: Distinguishes Pydantic models from SQLAlchemy database models
- **`Code*` prefix**: US Code entities (lines, sections, references)
- **`*Enum` suffix**: Enumeration types

## Current Structure

```
schemas/
├── __init__.py          # Re-exports all schemas
├── public_law.py        # PublicLawSchema, SourceLawSchema
├── us_code.py           # CodeLineSchema, SectionNotesSchema, etc.
└── validation.py        # Ingestion/parsing validation schemas
```

## Module Overview

### `public_law.py`
- `PublicLawSchema` - In-memory representation of a Public Law
- `SourceLawSchema` - Reference to a law that enacted/amended a section

### `us_code.py`
- `CodeLineSchema` - Single line of statutory text
- `CodeReferenceSchema` - In-text reference to another US Code section
- `AmendmentSchema` - Amendment record
- `ShortTitleSchema` - Common name for an act
- `NoteCategoryEnum` - Category of section notes
- `SectionNoteSchema` - Single note within a section
- `SectionNotesSchema` - Collection of notes for a section

### `validation.py`
Schemas for the ingestion validation system (parsing sessions, coverage reports, etc.)

## Future: In/Out Pattern

When building API endpoints, we plan to adopt the **In/Out pattern** for schemas that handle both input and output:

```python
# Shared fields
class PublicLawBase(BaseModel):
    congress: int
    law_number: int
    date: str | None = None

# Input - for API create/update endpoints (no auto-generated fields)
class PublicLawIn(PublicLawBase):
    pass

# Output - for API responses (includes DB fields + computed)
class PublicLawOut(PublicLawBase):
    id: int
    public_law_id: str  # computed
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

This pattern is valuable when:
- Input lacks auto-generated fields (id, timestamps)
- Output includes computed fields or relationships
- Security requires hiding sensitive fields from responses

The current `*Schema` classes serve as domain/transfer objects for the pipeline layer. They can be refactored into `*Base` classes when API endpoints are added.
