'use client';

interface LawTextViewerProps {
  content: string;
}

/** Renders raw law text (HTM or XML) in a code block with line numbers. */
export default function LawTextViewer({ content }: LawTextViewerProps) {
  const lines = content.split('\n');

  return (
    <div className="rounded bg-gray-100 py-2 pr-8 font-mono text-sm leading-relaxed">
      {lines.map((line, i) => (
        <div key={i} className="flex items-start">
          <span className="w-12 shrink-0 select-none text-right text-gray-400">
            {i + 1}
          </span>
          <span className="mx-2 select-none text-gray-400">│</span>
          <span className="min-w-0 whitespace-pre-wrap text-gray-800">
            {line}
          </span>
        </div>
      ))}
    </div>
  );
}
