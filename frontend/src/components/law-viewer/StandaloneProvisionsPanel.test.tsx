import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import StandaloneProvisionsPanel from './StandaloneProvisionsPanel';
import type { StandaloneProvision } from '@/lib/types';

const makeProvision = (
  overrides: Partial<StandaloneProvision> = {}
): StandaloneProvision => ({
  section_num: 'Sec. 3.',
  heading: 'Liberty Bridge Naming',
  text_excerpt: 'The bridge shall be known as the Liberty Bridge.',
  full_text: 'The bridge shall be known as the Liberty Bridge.',
  govinfo_url:
    'https://www.govinfo.gov/content/pkg/PLAW-113publ23/htm/PLAW-113publ23.htm',
  ...overrides,
});

describe('StandaloneProvisionsPanel', () => {
  it('renders collapsed by default', () => {
    render(<StandaloneProvisionsPanel provisions={[makeProvision()]} />);
    expect(
      screen.queryByText('The bridge shall be known as the Liberty Bridge.')
    ).toBeNull();
  });

  it('shows count badge with correct singular form', () => {
    render(<StandaloneProvisionsPanel provisions={[makeProvision()]} />);
    expect(screen.getByText('1 provision')).toBeTruthy();
  });

  it('shows count badge with correct plural form', () => {
    render(
      <StandaloneProvisionsPanel
        provisions={[
          makeProvision(),
          makeProvision({ section_num: 'Sec. 4.' }),
        ]}
      />
    );
    expect(screen.getByText('2 provisions')).toBeTruthy();
  });

  it('expands when header is clicked', () => {
    render(<StandaloneProvisionsPanel provisions={[makeProvision()]} />);
    fireEvent.click(screen.getByText('Standalone Provisions'));
    expect(
      screen.getByText('The bridge shall be known as the Liberty Bridge.')
    ).toBeTruthy();
  });

  it('shows section number and heading when expanded', () => {
    render(<StandaloneProvisionsPanel provisions={[makeProvision()]} />);
    fireEvent.click(screen.getByText('Standalone Provisions'));
    expect(screen.getByText('Sec. 3.')).toBeTruthy();
    expect(screen.getByText('Liberty Bridge Naming')).toBeTruthy();
  });

  it('shows "Not codified in US Code" label', () => {
    render(<StandaloneProvisionsPanel provisions={[makeProvision()]} />);
    fireEvent.click(screen.getByText('Standalone Provisions'));
    expect(screen.getByText('Not codified in US Code')).toBeTruthy();
  });

  it('shows GovInfo link when expanded', () => {
    render(<StandaloneProvisionsPanel provisions={[makeProvision()]} />);
    fireEvent.click(screen.getByText('Standalone Provisions'));
    const link = screen.getByText('View on GovInfo →');
    expect(link.getAttribute('href')).toContain('govinfo.gov');
  });

  it('does not show GovInfo link when url is null', () => {
    render(
      <StandaloneProvisionsPanel
        provisions={[makeProvision({ govinfo_url: null })]}
      />
    );
    fireEvent.click(screen.getByText('Standalone Provisions'));
    expect(screen.queryByText('View on GovInfo →')).toBeNull();
  });

  it('shows "Show full text" button when provision is truncated', () => {
    const longText = 'x'.repeat(600);
    const excerpt = longText.slice(0, 300) + '…';
    render(
      <StandaloneProvisionsPanel
        provisions={[
          makeProvision({ text_excerpt: excerpt, full_text: longText }),
        ]}
      />
    );
    fireEvent.click(screen.getByText('Standalone Provisions'));
    expect(screen.getByText('Show full text')).toBeTruthy();
  });

  it('does not show "Show full text" button when text is short', () => {
    const text = 'Short text.';
    render(
      <StandaloneProvisionsPanel
        provisions={[makeProvision({ text_excerpt: text, full_text: text })]}
      />
    );
    fireEvent.click(screen.getByText('Standalone Provisions'));
    expect(screen.queryByText('Show full text')).toBeNull();
  });

  it('expands individual provision text on "Show full text" click', () => {
    const fullText = 'x'.repeat(600);
    const excerpt = fullText.slice(0, 300) + '…';
    render(
      <StandaloneProvisionsPanel
        provisions={[
          makeProvision({ text_excerpt: excerpt, full_text: fullText }),
        ]}
      />
    );
    fireEvent.click(screen.getByText('Standalone Provisions'));
    fireEvent.click(screen.getByText('Show full text'));
    expect(screen.getByText('Show less')).toBeTruthy();
  });

  it('renders no heading when heading is null', () => {
    render(
      <StandaloneProvisionsPanel
        provisions={[makeProvision({ heading: null })]}
      />
    );
    fireEvent.click(screen.getByText('Standalone Provisions'));
    // Section num should still appear
    expect(screen.getByText('Sec. 3.')).toBeTruthy();
  });
});
