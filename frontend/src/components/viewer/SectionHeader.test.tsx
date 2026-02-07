import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import SectionHeader from './SectionHeader';

describe('SectionHeader', () => {
  it('renders citation and heading', () => {
    render(
      <SectionHeader
        fullCitation="17 U.S.C. § 106"
        heading="Exclusive rights in copyrighted works"
        enactedDate={null}
        lastModifiedDate={null}
        isPositiveLaw={false}
        isRepealed={false}
      />
    );
    expect(screen.getByText('17 U.S.C. § 106')).toBeInTheDocument();
    expect(
      screen.getByText('Exclusive rights in copyrighted works')
    ).toBeInTheDocument();
  });

  it('shows Positive Law badge when isPositiveLaw is true', () => {
    render(
      <SectionHeader
        fullCitation="17 U.S.C. § 106"
        heading="Test"
        enactedDate={null}
        lastModifiedDate={null}
        isPositiveLaw={true}
        isRepealed={false}
      />
    );
    expect(screen.getByText('Positive Law')).toBeInTheDocument();
  });

  it('shows Repealed badge when isRepealed is true', () => {
    render(
      <SectionHeader
        fullCitation="17 U.S.C. § 106"
        heading="Test"
        enactedDate={null}
        lastModifiedDate={null}
        isPositiveLaw={false}
        isRepealed={true}
      />
    );
    expect(screen.getByText('Repealed')).toBeInTheDocument();
  });

  it('shows enacted and last modified dates when provided', () => {
    render(
      <SectionHeader
        fullCitation="17 U.S.C. § 106"
        heading="Test"
        enactedDate="1976-10-19"
        lastModifiedDate="2020-01-01"
        isPositiveLaw={false}
        isRepealed={false}
      />
    );
    expect(screen.getByText('Enacted 1976-10-19')).toBeInTheDocument();
    expect(screen.getByText('Last modified 2020-01-01')).toBeInTheDocument();
  });

  it('hides dates when not provided', () => {
    render(
      <SectionHeader
        fullCitation="17 U.S.C. § 106"
        heading="Test"
        enactedDate={null}
        lastModifiedDate={null}
        isPositiveLaw={false}
        isRepealed={false}
      />
    );
    expect(screen.queryByText(/Enacted/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Last modified/)).not.toBeInTheDocument();
  });
});
