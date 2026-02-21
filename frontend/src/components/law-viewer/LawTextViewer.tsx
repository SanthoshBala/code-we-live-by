'use client';

interface LawTextViewerProps {
  content: string;
}

/** Strip HTML wrapper tags and decode HTML entities to plain text. */
function stripHtml(raw: string): string {
  // Remove <html>, <body>, <pre> wrappers (and closing tags)
  let text = raw.replace(/<\/?(html|body|pre)[^>]*>/gi, '');
  // Decode HTML entities (&lt; &gt; &amp; &quot; &#NNN; &#xHH;)
  const el =
    typeof document !== 'undefined' ? document.createElement('textarea') : null;
  if (el) {
    el.innerHTML = text;
    text = el.value;
  }
  // Remove GPO end-of-document marker <all>
  text = text.replace(/<all>\s*/gi, '');
  // Trim leading/trailing blank lines
  return text.replace(/^\n+/, '').replace(/\n+$/, '');
}

/** Renders raw law text (HTM or XML) in a code block with line numbers. */
export default function LawTextViewer({ content }: LawTextViewerProps) {
  const lines = stripHtml(content).split('\n');

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
