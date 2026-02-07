interface SectionHeaderProps {
  fullCitation: string;
  heading: string;
  enactedDate: string | null;
  lastModifiedDate: string | null;
  isPositiveLaw: boolean;
  isRepealed: boolean;
}

/** Renders the section heading, citation, and metadata badges. */
export default function SectionHeader({
  fullCitation,
  heading,
  enactedDate,
  lastModifiedDate,
  isPositiveLaw,
  isRepealed,
}: SectionHeaderProps) {
  return (
    <header className="mb-6">
      <h1 className="text-2xl font-bold text-gray-900">{fullCitation}</h1>
      <p className="mt-1 text-lg text-gray-600">{heading}</p>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        {isRepealed && (
          <span className="rounded-full bg-red-100 px-2.5 py-0.5 font-medium text-red-700">
            Repealed
          </span>
        )}
        {isPositiveLaw && (
          <span className="rounded-full bg-green-100 px-2.5 py-0.5 font-medium text-green-700">
            Positive Law
          </span>
        )}
        {enactedDate && (
          <span className="text-gray-500">Enacted {enactedDate}</span>
        )}
        {lastModifiedDate && (
          <span className="text-gray-500">
            Last modified {lastModifiedDate}
          </span>
        )}
      </div>
    </header>
  );
}
