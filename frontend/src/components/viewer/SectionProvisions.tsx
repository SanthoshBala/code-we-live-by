interface SectionProvisionsProps {
  textContent: string | null;
  isRepealed: boolean;
}

/** Renders the operative law text with whitespace-preserving layout. */
export default function SectionProvisions({
  textContent,
  isRepealed,
}: SectionProvisionsProps) {
  if (!textContent) {
    return (
      <div className="rounded border border-gray-200 bg-gray-50 px-4 py-6 text-center text-sm text-gray-500">
        {isRepealed
          ? 'This section has been repealed.'
          : 'No text content available for this section.'}
      </div>
    );
  }

  return (
    <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed text-gray-800">
      {textContent}
    </pre>
  );
}
