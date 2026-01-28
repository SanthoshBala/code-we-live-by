"""GovInfo API data ingestion for Public Laws."""

from pipeline.govinfo.client import GovInfoClient
from pipeline.govinfo.ingestion import PublicLawIngestionService

__all__ = ["GovInfoClient", "PublicLawIngestionService"]
