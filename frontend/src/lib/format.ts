const SMALL_WORDS = new Set([
  'a',
  'an',
  'and',
  'as',
  'at',
  'but',
  'by',
  'for',
  'in',
  'nor',
  'of',
  'on',
  'or',
  'so',
  'the',
  'to',
  'up',
  'yet',
]);

const ROMAN_NUMERAL = /^[IVXLCDM]+$/;

/** Convert an ALL-CAPS string to Title Case, preserving roman numerals. */
export function toTitleCase(text: string): string {
  return text
    .split(' ')
    .map((word, i) => {
      if (ROMAN_NUMERAL.test(word)) return word;
      const lower = word.toLowerCase();
      if (i > 0 && SMALL_WORDS.has(lower)) return lower;
      return lower.charAt(0).toUpperCase() + lower.slice(1);
    })
    .join(' ');
}
