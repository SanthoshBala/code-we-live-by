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
  note_categories?: string[];
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

// --- Tree navigator types ---

/** Identifies the active item in the tree so ancestors auto-expand and the node highlights. */
export interface TreeActivePath {
  titleNumber?: number;
  chapterNumber?: string;
  subchapterNumber?: string;
  sectionNumber?: string;
}

/** An item displayed in a directory table row. */
export interface DirectoryItem {
  id: string;
  name: string;
  href: string;
  kind: 'folder' | 'file';
  sectionCount?: number | null;
  lastAmendmentLaw?: string | null;
  lastAmendmentYear?: number | null;
}

/** A breadcrumb segment with label and optional link. */
export interface BreadcrumbSegment {
  label: string;
  href?: string;
}

// --- Section viewer types ---

/** A single line of rendered section content. */
export interface CodeLine {
  line_number: number;
  content: string;
  indent_level: number;
  marker: string | null;
  is_header: boolean;
}

/** A structured note attached to a section. */
export interface SectionNote {
  header: string;
  content: string;
  lines: CodeLine[];
  category: 'historical' | 'editorial' | 'statutory';
}

/** An amendment record for a section. */
export interface Amendment {
  law: {
    congress: number;
    law_number: number;
    public_law_id: string;
    date: string | null;
  };
  year: number;
  description: string;
  public_law_id: string;
}

/** A source law citation for a section. */
export interface SourceLaw {
  law_id: string;
  law_title: string | null;
  relationship: string;
  raw_text: string;
}

/** Aggregated notes, citations, and amendments for a section. */
export interface SectionNotes {
  citations: SourceLaw[];
  amendments: Amendment[];
  short_titles: {
    title: string;
    year: number | null;
    public_law: string | null;
  }[];
  notes: SectionNote[];
  has_notes: boolean;
  has_citations: boolean;
  has_amendments: boolean;
  transferred_to: string | null;
  omitted: boolean;
  renumbered_from: string | null;
}

/** Full section view returned by the section detail endpoint. */
export interface SectionView {
  title_number: number;
  section_number: string;
  heading: string;
  full_citation: string;
  text_content: string | null;
  provisions: CodeLine[] | null;
  enacted_date: string | null;
  last_modified_date: string | null;
  is_positive_law: boolean;
  is_repealed: boolean;
  notes: SectionNotes | null;
}
