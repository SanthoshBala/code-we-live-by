/**
 * Server-only API helpers for use in Next.js Server Components.
 *
 * Uses BACKEND_URL directly (bypassing the /api rewrite, which only applies
 * to client-originated requests). Never import this file in client components.
 */

import type { TitleSummary, PaginatedLaws } from './types';

function serverApiBase(): string {
  return `${process.env.BACKEND_URL ?? 'http://localhost:8000'}/api/v1`;
}

export async function fetchTitlesServer(): Promise<TitleSummary[]> {
  const res = await fetch(`${serverApiBase()}/titles/`);
  if (!res.ok) throw new Error(`Failed to fetch titles: ${res.status}`);
  return res.json() as Promise<TitleSummary[]>;
}

export async function fetchLawsServer(
  limit = 50,
  offset = 0
): Promise<PaginatedLaws> {
  const res = await fetch(
    `${serverApiBase()}/laws/?limit=${limit}&offset=${offset}`
  );
  if (!res.ok) throw new Error(`Failed to fetch laws: ${res.status}`);
  return res.json() as Promise<PaginatedLaws>;
}
