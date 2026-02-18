"""Chrono pipeline: amendment application engine.

Applies LawChange diffs to produce derived CodeRevisions with updated
SectionSnapshots. Phase 4 of the chrono pipeline:
    1.18 foundation → 1.19 bootstrap → 1.20 RP diffing →
    1.20b amendment application → 1.20c play-forward.
"""
