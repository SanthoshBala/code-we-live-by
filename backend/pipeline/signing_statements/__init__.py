"""Pipeline for scraping and storing presidential signing statements."""

from pipeline.signing_statements.ingestion import SigningStatementIngestionService
from pipeline.signing_statements.scraper import (
    SigningStatementResult,
    fetch_signing_statement,
)

__all__ = [
    "SigningStatementResult",
    "fetch_signing_statement",
    "SigningStatementIngestionService",
]
