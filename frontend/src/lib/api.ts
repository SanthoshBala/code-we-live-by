import type {
  TitleSummary,
  TitleStructure,
  SectionView,
  LawSummary,
  LawText,
  ParsedAmendment,
  SectionDiff,
  HeadRevision,
} from './types';

const API_BASE = '/api/v1';

/** Build a query string from optional params, omitting undefined values. */
function buildQuery(params: Record<string, string | undefined>): string {
  const entries = Object.entries(params).filter(
    (entry): entry is [string, string] => entry[1] !== undefined
  );
  if (entries.length === 0) return '';
  return '?' + new URLSearchParams(entries).toString();
}

/** Fetch all title summaries. */
export async function fetchTitles(revision?: number): Promise<TitleSummary[]> {
  const q = buildQuery({ revision: revision?.toString() });
  const res = await fetch(`${API_BASE}/titles/${q}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch titles: ${res.status}`);
  }
  return res.json();
}

/** Fetch the chapter/subchapter/section structure for a single title. */
export async function fetchTitleStructure(
  titleNumber: number,
  revision?: number
): Promise<TitleStructure> {
  const q = buildQuery({ revision: revision?.toString() });
  const res = await fetch(`${API_BASE}/titles/${titleNumber}/structure${q}`);
  if (!res.ok) {
    throw new Error(
      `Failed to fetch structure for title ${titleNumber}: ${res.status}`
    );
  }
  return res.json();
}

/** Fetch the full detail view for a single section. */
export async function fetchSection(
  titleNumber: number,
  sectionNumber: string,
  revision?: number
): Promise<SectionView> {
  const q = buildQuery({ revision: revision?.toString() });
  const res = await fetch(
    `${API_BASE}/sections/${titleNumber}/${encodeURIComponent(sectionNumber)}${q}`
  );
  if (!res.ok) {
    throw new Error(
      `Failed to fetch section ${titleNumber}/${sectionNumber}: ${res.status}`
    );
  }
  return res.json();
}

/** Fetch all public law summaries. */
export async function fetchLaws(): Promise<LawSummary[]> {
  const res = await fetch(`${API_BASE}/laws/`);
  if (!res.ok) {
    throw new Error(`Failed to fetch laws: ${res.status}`);
  }
  return res.json();
}

/** Fetch raw HTM and XML text for a public law. */
export async function fetchLawText(
  congress: number,
  lawNumber: string
): Promise<LawText> {
  const res = await fetch(
    `${API_BASE}/laws/${congress}/${encodeURIComponent(lawNumber)}/text`
  );
  if (!res.ok) {
    throw new Error(
      `Failed to fetch law text for PL ${congress}-${lawNumber}: ${res.status}`
    );
  }
  return res.json();
}

/** Fetch the HEAD (latest ingested) revision. */
export async function fetchHeadRevision(): Promise<HeadRevision> {
  const res = await fetch(`${API_BASE}/revisions/head`);
  if (!res.ok) {
    throw new Error(`Failed to fetch head revision: ${res.status}`);
  }
  return res.json();
}

/** Fetch metadata for a specific revision by ID. */
export async function fetchRevision(revisionId: number): Promise<HeadRevision> {
  const res = await fetch(`${API_BASE}/revisions/${revisionId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch revision ${revisionId}: ${res.status}`);
  }
  return res.json();
}

/** Fetch the most recent revision that affected any section in a title. */
export async function fetchLatestRevisionForTitle(
  titleNumber: number
): Promise<HeadRevision> {
  const res = await fetch(`${API_BASE}/revisions/latest?title=${titleNumber}`);
  if (!res.ok) {
    throw new Error(
      `Failed to fetch latest revision for title ${titleNumber}: ${res.status}`
    );
  }
  return res.json();
}

/** Fetch parsed amendments for a public law (live parse). */
export async function fetchLawAmendments(
  congress: number,
  lawNumber: string
): Promise<ParsedAmendment[]> {
  const res = await fetch(
    `${API_BASE}/laws/${congress}/${encodeURIComponent(lawNumber)}/amendments`
  );
  if (!res.ok) {
    throw new Error(
      `Failed to fetch amendments for PL ${congress}-${lawNumber}: ${res.status}`
    );
  }
  return res.json();
}

/** Fetch per-section unified diffs for a public law. */
export async function fetchLawDiffs(
  congress: number,
  lawNumber: string
): Promise<SectionDiff[]> {
  const res = await fetch(
    `${API_BASE}/laws/${congress}/${encodeURIComponent(lawNumber)}/diffs`
  );
  if (!res.ok) {
    throw new Error(
      `Failed to fetch diffs for PL ${congress}-${lawNumber}: ${res.status}`
    );
  }
  return res.json();
}
