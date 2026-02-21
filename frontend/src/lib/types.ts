// TypeScript interfaces mirroring backend Pydantic schemas
// for the US Code tree navigator.

/** Status of a code section or structural group. */
export type ItemStatus =
  | 'repealed'
  | 'reserved'
  | 'transferred'
  | 'renumbered'
  | 'omitted'
  | null;

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
  status?: ItemStatus;
  last_amendment_year?: number | null;
  last_amendment_law?: string | null;
  note_categories?: string[];
}

/** Recursive structural grouping node (title, subtitle, part, chapter, subchapter, division, etc.). */
export interface SectionGroupTree {
  group_type: string;
  number: string;
  name: string;
  sort_order: number;
  is_positive_law?: boolean;
  children: SectionGroupTree[];
  sections: SectionSummary[];
}

/** Full structure tree for a single title. */
export interface TitleStructure {
  title_number: number;
  title_name: string;
  is_positive_law: boolean;
  children: SectionGroupTree[];
  sections: SectionSummary[];
}

// --- Tree navigator types ---

/** Identifies the active item in the tree so ancestors auto-expand and the node highlights. */
export interface TreeActivePath {
  titleNumber?: number;
  sectionNumber?: string;
  groupPath?: { type: string; number: string }[];
}

/** An item displayed in a directory table row. */
export interface DirectoryItem {
  id: string;
  name: string;
  href: string;
  kind: 'folder' | 'file';
  status?: ItemStatus;
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
  is_signature?: boolean;
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
  law?: {
    congress: number;
    law_number: number;
    date: string | null;
    public_law_id: string;
  } | null;
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

// --- Revision types ---

/** HEAD revision metadata (latest ingested commit). */
export interface HeadRevision {
  revision_id: number;
  revision_type: string;
  effective_date: string;
  summary: string | null;
  sequence_number: number;
}

// --- Law viewer types ---

/** Summary of a Public Law for index listing. */
export interface LawSummary {
  congress: number;
  law_number: string;
  official_title: string | null;
  short_title: string | null;
  enacted_date: string;
  sections_affected: number;
}

/** Raw text content of a Public Law. */
export interface LawText {
  congress: number;
  law_number: string;
  official_title: string | null;
  short_title: string | null;
  enacted_date: string | null;
  introduced_date: string | null;
  house_passed_date: string | null;
  senate_passed_date: string | null;
  presented_to_president_date: string | null;
  effective_date: string | null;
  htm_content: string | null;
  xml_content: string | null;
}

/** A reference to a US Code section within a parsed amendment. */
export interface SectionReference {
  title: number | null;
  section: string;
  subsection_path: string | null;
  display: string;
}

/** Positional context for an amendment. */
export interface PositionQualifier {
  type: string;
  anchor_text: string | null;
  target_text: string | null;
}

/** A parsed amendment extracted from Public Law text. */
export interface ParsedAmendment {
  pattern_name: string;
  pattern_type: string;
  change_type: string;
  section_ref: SectionReference | null;
  old_text: string | null;
  new_text: string | null;
  full_match: string;
  confidence: number;
  needs_review: boolean;
  context: string;
  position_qualifier: PositionQualifier | null;
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
  last_revision?: HeadRevision | null;
}
