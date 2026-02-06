// TypeScript interfaces mirroring backend Pydantic schemas
// for the US Code tree navigator.

/** Summary of a US Code title for list views. */
export interface TitleSummary {
  title_number: number;
  title_name: string;
  is_positive_law: boolean;
  positive_law_date: string | null;
  chapter_count: number;
  section_count: number;
}

/** Lightweight section reference within a tree view. */
export interface SectionSummary {
  section_number: string;
  heading: string;
  sort_order: number;
  last_amendment_year?: number | null;
  last_amendment_law?: string | null;
}

/** Subchapter node in the title structure tree. */
export interface SubchapterTree {
  subchapter_number: string;
  subchapter_name: string;
  sort_order: number;
  sections: SectionSummary[];
}

/** Chapter node in the title structure tree. */
export interface ChapterTree {
  chapter_number: string;
  chapter_name: string;
  sort_order: number;
  subchapters: SubchapterTree[];
  sections: SectionSummary[];
}

/** Full structure tree for a single title. */
export interface TitleStructure {
  title_number: number;
  title_name: string;
  is_positive_law: boolean;
  chapters: ChapterTree[];
}
