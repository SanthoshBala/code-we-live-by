import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { linkifyContent } from './linkifyContent';
import type { NoteReference } from '@/lib/types';

vi.mock('next/link', () => ({
  default: ({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) => <a href={href}>{children}</a>,
}));

const identity = (href: string) => href;

function makeRef(overrides: Partial<NoteReference>): NoteReference {
  return {
    ref_type: 'usc_section',
    href: '',
    display_text: '',
    congress: null,
    law_number: null,
    usc_title: null,
    usc_section: null,
    target_id: '',
    resolvable: true,
    ...overrides,
  };
}

describe('linkifyContent', () => {
  it('returns plain text when no references', () => {
    const result = linkifyContent('Hello world', [], identity);
    expect(result).toBe('Hello world');
  });

  it('wraps USC section references as internal links', () => {
    const refs: NoteReference[] = [
      makeRef({
        ref_type: 'usc_section',
        display_text: 'section 106 of title 17',
        usc_title: 17,
        usc_section: '106',
        target_id: '17 USC 106',
      }),
    ];
    const result = linkifyContent(
      'See section 106 of title 17 for details.',
      refs,
      identity
    );
    render(<span>{result}</span>);
    const link = screen.getByRole('link', {
      name: 'section 106 of title 17',
    });
    expect(link).toHaveAttribute('href', '/sections/17/106');
  });

  it('wraps public law references as internal links', () => {
    const refs: NoteReference[] = [
      makeRef({
        ref_type: 'public_law',
        display_text: 'Pub. L. 115–264',
        congress: 115,
        law_number: 264,
        target_id: 'PL 115-264',
      }),
    ];
    const result = linkifyContent(
      'Enacted by Pub. L. 115–264.',
      refs,
      identity
    );
    render(<span>{result}</span>);
    const link = screen.getByRole('link', { name: 'Pub. L. 115–264' });
    expect(link).toHaveAttribute('href', '/laws/115/264');
  });

  it('renders act references as styled text without link', () => {
    const refs: NoteReference[] = [
      makeRef({
        ref_type: 'act',
        display_text: 'Social Security Act',
        target_id: 'Act of 1935-08-14 ch. 531',
      }),
    ];
    const result = linkifyContent(
      'The Social Security Act applies.',
      refs,
      identity
    );
    render(<span>{result}</span>);
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    expect(screen.getByText('Social Security Act')).toBeInTheDocument();
  });

  it('applies withRev to generated hrefs', () => {
    const refs: NoteReference[] = [
      makeRef({
        ref_type: 'usc_section',
        display_text: 'section 106',
        usc_title: 17,
        usc_section: '106',
        target_id: '17 USC 106',
      }),
    ];
    const withRev = (href: string) => `${href}?rev=3`;
    const result = linkifyContent('See section 106.', refs, withRev);
    render(<span>{result}</span>);
    const link = screen.getByRole('link', { name: 'section 106' });
    expect(link).toHaveAttribute('href', '/sections/17/106?rev=3');
  });

  it('handles multiple references in the same text', () => {
    const refs: NoteReference[] = [
      makeRef({
        ref_type: 'usc_section',
        display_text: 'section 106',
        usc_title: 17,
        usc_section: '106',
        target_id: '17 USC 106',
      }),
      makeRef({
        ref_type: 'public_law',
        display_text: 'Pub. L. 115–264',
        congress: 115,
        law_number: 264,
        target_id: 'PL 115-264',
      }),
    ];
    const result = linkifyContent(
      'Amended section 106 by Pub. L. 115–264.',
      refs,
      identity
    );
    render(<span>{result}</span>);
    expect(screen.getAllByRole('link')).toHaveLength(2);
  });

  it('prefers longer matches over shorter ones', () => {
    const refs: NoteReference[] = [
      makeRef({
        ref_type: 'usc_section',
        display_text: 'section 106',
        usc_title: 17,
        usc_section: '106',
        target_id: '17 USC 106',
      }),
      makeRef({
        ref_type: 'usc_section',
        display_text: 'section 106 of title 17',
        usc_title: 17,
        usc_section: '106',
        target_id: '17 USC 106',
      }),
    ];
    const result = linkifyContent(
      'See section 106 of title 17.',
      refs,
      identity
    );
    render(<span>{result}</span>);
    // Should produce one link for the longer match, not two
    const links = screen.getAllByRole('link');
    expect(links).toHaveLength(1);
    expect(links[0]).toHaveTextContent('section 106 of title 17');
  });

  it('renders non-resolvable refs as styled text, not links', () => {
    const refs: NoteReference[] = [
      makeRef({
        ref_type: 'public_law',
        display_text: 'Pub. L. 99–999',
        congress: 99,
        law_number: 999,
        target_id: 'PL 99-999',
        resolvable: false,
      }),
    ];
    const result = linkifyContent(
      'See Pub. L. 99–999 for details.',
      refs,
      identity
    );
    render(<span>{result}</span>);
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    expect(screen.getByText('Pub. L. 99–999')).toBeInTheDocument();
  });
});
