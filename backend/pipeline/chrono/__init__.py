"""Chrono pipeline: amendment application & play-forward engine.

Phase 4: Applies LawChange diffs to produce derived CodeRevisions.
Phase 5: Walks the timeline forward, coordinating law application and
RP ingestion with checkpoint validation.

Pipeline: 1.18 foundation → 1.19 bootstrap → 1.20 RP diffing →
    1.20b amendment application → 1.20c play-forward.
"""
