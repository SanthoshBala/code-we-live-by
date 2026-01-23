#!/usr/bin/env python3
"""
Prototype Parser for Public Laws

Task 0.5: Build prototype parser for single Public Law (PL 94-553)

This prototype demonstrates:
1. Fetching law metadata from GovInfo API
2. Parsing legal language for amendment patterns
3. Extracting section changes
4. Generating diffs between old and new text

Author: CWLB Development Team
Date: 2026-01-23
"""

import requests
import json
import re
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from difflib import unified_diff
from collections import Counter


# Configuration
GOVINFO_API_KEY = os.getenv('GOVINFO_API_KEY', 'DEMO_KEY')
GOVINFO_BASE_URL = 'https://api.govinfo.gov'


@dataclass
class LawMetadata:
    """Structured metadata for a Public Law."""
    package_id: str
    title: str
    short_title: Optional[str]
    date_issued: str
    congress: int
    session: Optional[int]
    law_number: str
    law_type: str


@dataclass
class SectionChange:
    """Represents a change to a US Code section."""
    title: int
    section: str
    change_type: str  # 'amended', 'added', 'repealed'
    old_text: Optional[str] = None
    new_text: Optional[str] = None

    def __str__(self):
        return f"{self.title} USC § {self.section} ({self.change_type})"


class PublicLawParser:
    """Parser for Public Law documents."""

    # Common legal language patterns for amendments
    AMENDMENT_PATTERNS = {
        'section_amended': r'Section\s+(\d+[A-Za-z]?)\s+(?:of title (\d+))?.*?is amended',
        'strike_insert': r'striking\s+["\'](.+?)["\']\s+and inserting\s+["\'](.+?)["\']',
        'add_at_end': r'adding at the end(?:\s+thereof)?\s+the following',
        'section_repealed': r'Section\s+(\d+[A-Za-z]?).*?is(?:\s+hereby)?\s+repealed',
        'title_amended': r'Title\s+(\d+).*?is amended',
        'insert_after': r'inserting after section\s+(\d+[A-Za-z]?)\s+the following',
    }

    def __init__(self, api_key: str = GOVINFO_API_KEY):
        """Initialize parser with API key."""
        self.api_key = api_key
        self.session = requests.Session()

    def fetch_package_summary(self, package_id: str) -> Dict:
        """Fetch package summary metadata from GovInfo API."""
        url = f"{GOVINFO_BASE_URL}/packages/{package_id}/summary"
        params = {'api_key': self.api_key}

        response = self.session.get(url, params=params)
        response.raise_for_status()

        return response.json()

    def fetch_law_text(self, package_id: str, format_type: str = 'htm') -> str:
        """Fetch law text content from GovInfo."""
        url = f"{GOVINFO_BASE_URL}/packages/{package_id}/{format_type}"
        params = {'api_key': self.api_key}

        response = self.session.get(url, params=params)
        response.raise_for_status()

        return response.text

    def parse_metadata(self, summary: Dict) -> LawMetadata:
        """Extract and structure law metadata."""
        # Parse law number from package ID
        # Format: PLAW-{congress}publ{number}
        law_number = None
        match = re.match(r'PLAW-(\d+)publ(\d+)', summary.get('packageId', ''))
        if match:
            congress_num = match.group(1)
            law_num = match.group(2)
            law_number = f"{congress_num}-{law_num}"

        return LawMetadata(
            package_id=summary.get('packageId'),
            title=summary.get('title'),
            short_title=summary.get('shortTitle'),
            date_issued=summary.get('dateIssued'),
            congress=summary.get('congress'),
            session=summary.get('session'),
            law_number=law_number,
            law_type='Public Law'
        )

    def find_amendment_patterns(self, text: str) -> List[Tuple[str, str]]:
        """Find all amendment patterns in law text."""
        findings = []

        for pattern_name, pattern in self.AMENDMENT_PATTERNS.items():
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                findings.append((pattern_name, match.group(0)))

        return findings

    def extract_section_changes(self, text: str, title: int = 17) -> List[SectionChange]:
        """Extract section changes from law text."""
        changes = []

        # Pattern 1: Section X is amended
        amended_pattern = r'Section\s+(\d+[A-Za-z]?).*?is amended'
        for match in re.finditer(amended_pattern, text, re.IGNORECASE):
            section = match.group(1)
            changes.append(SectionChange(
                title=title,
                section=section,
                change_type='amended'
            ))

        # Pattern 2: Section X is repealed
        repealed_pattern = r'Section\s+(\d+[A-Za-z]?).*?is(?:\s+hereby)?\s+repealed'
        for match in re.finditer(repealed_pattern, text, re.IGNORECASE):
            section = match.group(1)
            changes.append(SectionChange(
                title=title,
                section=section,
                change_type='repealed'
            ))

        return changes

    @staticmethod
    def generate_diff(old_text: str, new_text: str, section_ref: str) -> List[str]:
        """Generate unified diff between old and new section text."""
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)

        diff = list(unified_diff(
            old_lines,
            new_lines,
            fromfile=f"{section_ref} (before)",
            tofile=f"{section_ref} (after)",
            lineterm=''
        ))

        return diff

    @staticmethod
    def analyze_diff_statistics(old_text: str, new_text: str) -> Dict:
        """Calculate statistics about the changes."""
        old_lines = old_text.splitlines()
        new_lines = new_text.splitlines()

        diff_lines = list(unified_diff(old_lines, new_lines))

        return {
            'old_line_count': len(old_lines),
            'new_line_count': len(new_lines),
            'lines_added': sum(1 for line in diff_lines if line.startswith('+')),
            'lines_removed': sum(1 for line in diff_lines if line.startswith('-')),
        }


def main():
    """Main function to demonstrate prototype parser."""
    print("=" * 70)
    print("PROTOTYPE PARSER FOR PUBLIC LAW 94-553")
    print("(Copyright Act of 1976)")
    print("=" * 70)

    parser = PublicLawParser()
    package_id = 'PLAW-94publ553'

    # Step 1: Fetch metadata
    print("\n1. Fetching law metadata...")
    try:
        summary = parser.fetch_package_summary(package_id)
        metadata = parser.parse_metadata(summary)

        print(f"   ✓ Title: {metadata.title[:80]}...")
        print(f"   ✓ Law Number: PL {metadata.law_number}")
        print(f"   ✓ Date Issued: {metadata.date_issued}")
        print(f"   ✓ Congress: {metadata.congress}")
    except Exception as e:
        print(f"   ✗ Error fetching metadata: {e}")
        return

    # Step 2: Fetch law text
    print("\n2. Fetching law text...")
    try:
        law_text = parser.fetch_law_text(package_id, 'htm')
        print(f"   ✓ Successfully fetched {len(law_text):,} characters")
    except Exception as e:
        print(f"   ✗ Error fetching law text: {e}")
        print("   → Using mock data for demonstration")
        law_text = "Section 106 is amended by striking..."

    # Step 3: Find amendment patterns
    print("\n3. Analyzing amendment patterns...")
    patterns_found = parser.find_amendment_patterns(law_text)
    print(f"   ✓ Found {len(patterns_found)} potential amendments")

    pattern_types = Counter([p[0] for p in patterns_found])
    for pattern_type, count in pattern_types.most_common():
        print(f"     - {pattern_type}: {count}")

    # Step 4: Extract section changes
    print("\n4. Extracting section changes...")
    section_changes = parser.extract_section_changes(law_text, title=17)
    print(f"   ✓ Identified {len(section_changes)} section changes")

    change_types = Counter([c.change_type for c in section_changes])
    for change_type, count in change_types.items():
        print(f"     - {change_type}: {count}")

    if section_changes:
        print(f"\n   Sample changes:")
        for change in section_changes[:5]:
            print(f"     • {change}")

    # Step 5: Demonstrate diff generation
    print("\n5. Demonstrating diff generation (mock data)...")

    old_text = """§ 106. Exclusive rights in copyrighted works
Subject to sections 107 through 120, the owner of copyright has exclusive rights."""

    new_text = """§ 106. Exclusive rights in copyrighted works
Subject to sections 107 through 122, the owner of copyright has exclusive rights.

(1) to reproduce the copyrighted work;
(2) to prepare derivative works;"""

    diff = parser.generate_diff(old_text, new_text, "17 USC § 106")
    stats = parser.analyze_diff_statistics(old_text, new_text)

    print(f"   ✓ Generated diff:")
    print(f"     - Lines added: {stats['lines_added']}")
    print(f"     - Lines removed: {stats['lines_removed']}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY AND FINDINGS")
    print("=" * 70)

    print("\n✓ SUCCESSFUL CAPABILITIES:")
    print("  • Fetch law metadata from GovInfo API")
    print("  • Parse law number, date, congress from metadata")
    print("  • Identify common amendment patterns in legal text")
    print("  • Extract section numbers being modified")
    print("  • Classify change types (amended, repealed)")
    print("  • Generate unified diffs between text versions")

    print("\n⚠ CHALLENGES IDENTIFIED:")
    print("  • Legal language is highly variable and complex")
    print("  • Extracting exact new text from amendments is difficult")
    print("  • Need historical US Code text for accurate diffs")
    print("  • Complex nested amendments may require manual review")

    print("\n→ RECOMMENDATIONS:")
    print("  1. Focus on modern laws (113th Congress+) with USLM XML")
    print("  2. Build comprehensive pattern library for amendments")
    print("  3. Implement manual review workflow for edge cases")
    print("  4. Integrate with US Code API for before/after text")
    print("  5. Start with well-structured laws for initial testing")

    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()
