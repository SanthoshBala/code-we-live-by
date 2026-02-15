'use client';

import type { ParsedAmendment } from '@/lib/types';

interface AffectedSectionsTreeProps {
  amendments: ParsedAmendment[];
  activeSection: string | null;
  onSectionClick: (sectionKey: string) => void;
}

interface SectionGroup {
  key: string;
  title: number | null;
  section: string;
  display: string;
  count: number;
}

/** Groups amendments by target section and builds a sidebar tree. */
function buildSectionGroups(amendments: ParsedAmendment[]): SectionGroup[] {
  const groupMap = new Map<string, SectionGroup>();

  for (const a of amendments) {
    if (!a.section_ref) continue;
    const key = a.section_ref.display || `§ ${a.section_ref.section}`;
    const existing = groupMap.get(key);
    if (existing) {
      existing.count++;
    } else {
      groupMap.set(key, {
        key,
        title: a.section_ref.title,
        section: a.section_ref.section,
        display: key,
        count: 1,
      });
    }
  }

  // Sort by title then section
  return Array.from(groupMap.values()).sort((a, b) => {
    const titleDiff = (a.title ?? 0) - (b.title ?? 0);
    if (titleDiff !== 0) return titleDiff;
    return a.section.localeCompare(b.section, undefined, { numeric: true });
  });
}

/** Groups section groups by title number for tree display. */
function groupByTitle(groups: SectionGroup[]): Map<string, SectionGroup[]> {
  const titleMap = new Map<string, SectionGroup[]>();
  for (const g of groups) {
    const titleKey = g.title != null ? `Title ${g.title}` : 'Unknown Title';
    const existing = titleMap.get(titleKey);
    if (existing) {
      existing.push(g);
    } else {
      titleMap.set(titleKey, [g]);
    }
  }
  return titleMap;
}

/** Sidebar tree of USC sections affected by a law, grouped by title. */
export default function AffectedSectionsTree({
  amendments,
  activeSection,
  onSectionClick,
}: AffectedSectionsTreeProps) {
  const sectionGroups = buildSectionGroups(amendments);
  const titleGroups = groupByTitle(sectionGroups);

  if (sectionGroups.length === 0) {
    return (
      <p className="px-3 py-2 text-sm text-gray-500">
        No section references found.
      </p>
    );
  }

  return (
    <nav className="space-y-3">
      {Array.from(titleGroups.entries()).map(([titleLabel, sections]) => (
        <div key={titleLabel}>
          <h3 className="px-3 text-xs font-semibold uppercase tracking-wider text-gray-500">
            {titleLabel}
          </h3>
          <ul className="mt-1 space-y-0.5">
            {sections.map((sg) => (
              <li key={sg.key}>
                <button
                  onClick={() => onSectionClick(sg.key)}
                  className={`w-full rounded px-3 py-1.5 text-left text-sm ${
                    activeSection === sg.key
                      ? 'bg-primary-50 font-medium text-primary-700'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  <span>{sg.display}</span>
                  <span className="ml-1 text-xs text-gray-400">
                    ({sg.count})
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}
