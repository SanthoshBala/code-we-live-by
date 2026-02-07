interface SectionProvisionsProps {
  textContent: string | null;
  isRepealed: boolean;
}

/** Renders the operative law text as numbered lines like a code file. */
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

  const lines = textContent.split('\n');

  return (
    <div className="rounded bg-gray-50 py-2 font-mono text-sm leading-relaxed">
      {lines.map((line, i) => (
        <div key={i} className="flex">
          <span className="w-10 shrink-0 select-none text-right text-gray-400">
            {i + 1}
          </span>
          <span className="mx-2 select-none text-gray-400">│</span>
          <span className="whitespace-pre-wrap text-gray-800">{line}</span>
        </div>
      ))}
    </div>
  );
}
