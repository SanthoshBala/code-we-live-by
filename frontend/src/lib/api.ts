import type { TitleSummary, TitleStructure, SectionView } from './types';

const API_BASE = '/api/v1';

/** Fetch all title summaries. */
export async function fetchTitles(): Promise<TitleSummary[]> {
  const res = await fetch(`${API_BASE}/titles/`);
  if (!res.ok) {
    throw new Error(`Failed to fetch titles: ${res.status}`);
  }
  return res.json();
}

/** Fetch the chapter/subchapter/section structure for a single title. */
export async function fetchTitleStructure(
  titleNumber: number
): Promise<TitleStructure> {
  const res = await fetch(`${API_BASE}/titles/${titleNumber}/structure`);
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
  sectionNumber: string
): Promise<SectionView> {
  const res = await fetch(
    `${API_BASE}/sections/${titleNumber}/${sectionNumber}`
  );
  if (!res.ok) {
    throw new Error(
      `Failed to fetch section ${titleNumber}/${sectionNumber}: ${res.status}`
    );
  }
  return res.json();
}
