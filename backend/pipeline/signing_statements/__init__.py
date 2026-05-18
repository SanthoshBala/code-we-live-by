"""Pipeline for fetching and storing presidential signing statements from GovInfo."""

from pipeline.signing_statements.fetcher import (
    SigningStatementResult,
    fetch_signing_statement,
)
from pipeline.signing_statements.ingestion import SigningStatementIngestionService

__all__ = [
    "SigningStatementResult",
    "fetch_signing_statement",
    "SigningStatementIngestionService",
]
