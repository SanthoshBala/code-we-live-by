'use client';

import { useState } from 'react';

interface SectionProvisionsProps {
  fullCitation: string;
  heading: string;
  textContent: string | null;
  isRepealed: boolean;
}

function isHeaderLine(text: string): boolean {
  if (!/^\([a-zA-Z0-9]+\)/.test(text)) return false;
  if (text.length > 80) return false;
  if (/[.;,:]$/.test(text)) return false;
  return true;
}

const headerStyles = {
  1: 'font-bold text-blue-700',
  2: 'font-bold text-gray-900',
  3: 'font-bold text-violet-700',
} as const;

/** Renders the operative law text as numbered lines like a code file. */
export default function SectionProvisions({
  fullCitation,
  heading,
  textContent,
  isRepealed,
}: SectionProvisionsProps) {
  const [headerStyle, setHeaderStyle] = useState<1 | 2 | 3>(1);

  if (!textContent) {
    return (
      <div className="rounded border border-gray-200 bg-gray-50 px-4 py-6 text-center text-sm text-gray-500">
        {isRepealed
          ? 'This section has been repealed.'
          : 'No text content available for this section.'}
      </div>
    );
  }

  const docstring = [fullCitation, heading];
  const blankLineNumber = docstring.length + 1;
  const lines = textContent.split('\n');

  return (
    <div>
      <div className="mb-2 flex items-center gap-1">
        <span className="mr-1 text-xs text-gray-500">Headers:</span>
        {([1, 2, 3] as const).map((style) => (
          <button
            key={style}
            onClick={() => setHeaderStyle(style)}
            className={`rounded-full px-2 py-0.5 text-xs font-medium transition-colors ${
              headerStyle === style
                ? style === 1
                  ? 'bg-blue-100 text-blue-700'
                  : style === 2
                    ? 'bg-gray-200 text-gray-900'
                    : 'bg-violet-100 text-violet-700'
                : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
            }`}
          >
            {style === 1 ? 'Blue' : style === 2 ? 'Bold' : 'Purple'}
          </button>
        ))}
      </div>
      <div className="rounded bg-gray-100 py-2 pr-8 font-mono text-sm leading-relaxed">
        {docstring.map((text, i) => (
          <div key={`doc-${i}`} className="flex items-start text-green-700">
            <span className="w-10 shrink-0 select-none text-right text-gray-400">
              {i + 1}
            </span>
            <span className="mx-2 select-none text-gray-400">│</span>
            <span className="min-w-0 pl-[4ch] -indent-[4ch]">
              <span className="select-none"># </span>
              {text}
            </span>
          </div>
        ))}
        <div className="flex">
          <span className="w-10 shrink-0 select-none text-right text-gray-400">
            {blankLineNumber}
          </span>
          <span className="mx-2 select-none text-gray-400">│</span>
        </div>
        {lines.map((line, i) => {
          const match = line.match(/^(\s*)(.*)/);
          const indent = match?.[1] ?? '';
          const text = match?.[2] ?? line;
          const isListItem = /^\([a-zA-Z0-9]+\)/.test(text);
          const isHeader = isHeaderLine(text);
          return (
            <div key={i} className="flex items-start">
              <span className="w-10 shrink-0 select-none text-right text-gray-400">
                {i + 1 + blankLineNumber}
              </span>
              <span className="mx-2 select-none text-gray-400">│</span>
              {indent && (
                <span className="shrink-0 whitespace-pre text-gray-800">
                  {indent}
                </span>
              )}
              <span
                className={`min-w-0 whitespace-pre-wrap ${isHeader ? headerStyles[headerStyle] : 'text-gray-800'}${isListItem ? ' pl-[4ch] -indent-[4ch]' : ''}`}
              >
                {text}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
