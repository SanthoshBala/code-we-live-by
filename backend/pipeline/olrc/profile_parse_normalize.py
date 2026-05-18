"""Profiling script for USLMParser.parse_file and normalize_parsed_section.

Usage (from backend/ directory):
    uv run python -m pipeline.olrc.profile_parse_normalize [xml_path...]

If no paths are given, a synthetic XML file is generated that mimics the
structure of a large title (deep nesting, continuation elements, notes).

Output: cProfile stats sorted by cumulative time, written to stdout and
optionally to a .prof file for visualization with snakeviz:
    uv run snakeviz parse_normalize.prof
"""

from __future__ import annotations

import cProfile
import io
import pstats
import sys
import tempfile
import time
from pathlib import Path
from textwrap import dedent

from pipeline.olrc.normalized_section import normalize_parsed_section
from pipeline.olrc.parser import USLMParser, USLMParseResult

# ---------------------------------------------------------------------------
# Synthetic XML generation
# ---------------------------------------------------------------------------

_SECTION_TMPL = """\
<section identifier="/us/usc/t26/s{num}" number="{num}">
  <num value="{num}">§ {num}.</num>
  <heading>{heading}</heading>
  <subsection identifier="/us/usc/t26/s{num}/ss_a">
    <num>(a)</num>
    <heading>General rule</heading>
    <chapeau>In the case of any individual, gross income includes all of the following:</chapeau>
    <paragraph identifier="/us/usc/t26/s{num}/ss_a/p1">
      <num>(1)</num>
      <content>Compensation for services, including fees, commissions, fringe benefits, and similar items.</content>
    </paragraph>
    <paragraph identifier="/us/usc/t26/s{num}/ss_a/p2">
      <num>(2)</num>
      <content>Gross income derived from business.</content>
    </paragraph>
    <paragraph identifier="/us/usc/t26/s{num}/ss_a/p3">
      <num>(3)</num>
      <heading>Capital gains</heading>
      <chapeau>Gains derived from dealings in property including:</chapeau>
      <subparagraph>
        <num>(A)</num>
        <content>Real property.</content>
      </subparagraph>
      <subparagraph>
        <num>(B)</num>
        <content>Personal property held for investment.</content>
      </subparagraph>
      <continuation>to the extent not excluded under subsection (b).</continuation>
    </paragraph>
  </subsection>
  <subsection identifier="/us/usc/t26/s{num}/ss_b">
    <num>(b)</num>
    <heading>Exclusions from gross income</heading>
    <content>The following items shall be excluded from gross income:
    amounts received under workmen's compensation acts; amounts received
    through accident or health insurance; the value of property acquired by
    gift, bequest, devise, or inheritance.</content>
  </subsection>
  <sourceCredit>(Pub. L. 86-272, title I, § {num}, Aug. 28, 1958, 72 Stat. 1606.)</sourceCredit>
  <notes>
    <note type="historicalAndRevision"><heading class="smallCaps">Historical and Revision Notes</heading>
    <p>Based on 26 U.S.C., 1940 ed., § {num} (Feb. 10, 1939, ch. 2, § {num}, 53 Stat. 5).</p>
    <p>Minor changes were made in phraseology.</p>
    </note>
  </notes>
</section>
"""


def _make_synthetic_xml(section_count: int = 500) -> str:
    """Generate a synthetic USLM XML document with *section_count* sections."""
    sections = "\n".join(
        _SECTION_TMPL.format(num=i + 1, heading=f"Definition of item {i + 1}")
        for i in range(section_count)
    )
    return dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <usc xmlns="http://xml.house.gov/schemas/uslm/1.0">
          <meta>
            <docNumber>26</docNumber>
            <property role="is-positive-law">no</property>
          </meta>
          <main>
            <title identifier="/us/usc/t26" number="26">
              <num value="26">Title 26</num>
              <heading>INTERNAL REVENUE CODE</heading>
              <chapter identifier="/us/usc/t26/ch1" number="1">
                <heading>Normal Taxes and Surtaxes</heading>
                {sections}
              </chapter>
            </title>
          </main>
        </usc>
    """)


# ---------------------------------------------------------------------------
# Profiling helpers
# ---------------------------------------------------------------------------


def _print_stats(pr: cProfile.Profile, top_n: int = 25) -> None:
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps.print_stats(top_n)
    print(s.getvalue())


def profile_parse(xml_path: Path, save_prof: Path | None = None) -> USLMParseResult:
    print(f"\n{'=' * 60}")
    print(f"PARSE: {xml_path.name}")
    print("=" * 60)

    pr = cProfile.Profile()
    pr.enable()
    t0 = time.monotonic()
    result = USLMParser().parse_file(xml_path)
    elapsed = time.monotonic() - t0
    pr.disable()

    section_count = len(result.sections)
    ms_per_section = elapsed * 1000 / section_count if section_count else 0
    print(f"  {section_count} sections in {elapsed:.2f}s  ({ms_per_section:.2f} ms/§)")
    _print_stats(pr)

    if save_prof:
        pr.dump_stats(str(save_prof))
        print(f"  Profile saved → {save_prof}")

    return result


def profile_normalize(
    result: USLMParseResult, title_label: str = "", save_prof: Path | None = None
) -> None:
    print(f"\n{'=' * 60}")
    print(f"NORMALIZE: {title_label or 'unknown'}")
    print("=" * 60)

    pr = cProfile.Profile()
    pr.enable()
    t0 = time.monotonic()
    for section in result.sections:
        normalize_parsed_section(section)
    elapsed = time.monotonic() - t0
    pr.disable()

    section_count = len(result.sections)
    ms_per_section = elapsed * 1000 / section_count if section_count else 0
    print(f"  {section_count} sections in {elapsed:.2f}s  ({ms_per_section:.2f} ms/§)")
    _print_stats(pr)

    if save_prof:
        pr.dump_stats(str(save_prof))
        print(f"  Profile saved → {save_prof}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str]) -> None:
    xml_paths: list[Path] = [Path(p) for p in argv if argv]

    if not xml_paths:
        print(
            "No XML paths given — generating synthetic Title-26-style XML (500 sections)…"
        )
        with tempfile.NamedTemporaryFile(
            suffix=".xml", delete=False, mode="w", encoding="utf-8"
        ) as f:
            f.write(_make_synthetic_xml(section_count=500))
            tmp_path = Path(f.name)
        xml_paths = [tmp_path]
        cleanup = True
    else:
        cleanup = False

    try:
        for xml_path in xml_paths:
            parse_prof = Path(f"parse_{xml_path.stem}.prof")
            norm_prof = Path(f"normalize_{xml_path.stem}.prof")

            result = profile_parse(xml_path, save_prof=parse_prof)
            profile_normalize(result, title_label=xml_path.name, save_prof=norm_prof)

        print(
            "\nTip: visualize with  uv run snakeviz parse_<name>.prof\n"
            "     or              uv run snakeviz normalize_<name>.prof"
        )
    finally:
        if cleanup:
            tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main(sys.argv[1:])
