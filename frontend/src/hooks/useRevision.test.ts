import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useRevision } from './useRevision';

const mockGet = vi.fn();
vi.mock('next/navigation', () => ({
  useSearchParams: () => ({
    get: mockGet,
  }),
}));

describe('useRevision', () => {
  beforeEach(() => {
    mockGet.mockReset();
  });

  it('returns undefined revision when no ?rev= param', () => {
    mockGet.mockReturnValue(null);

    const { result } = renderHook(() => useRevision());

    expect(result.current.revision).toBeUndefined();
  });

  it('parses ?rev= param as number', () => {
    mockGet.mockReturnValue('42');

    const { result } = renderHook(() => useRevision());

    expect(result.current.revision).toBe(42);
  });

  describe('withRev helper', () => {
    it('returns href unchanged when no revision', () => {
      mockGet.mockReturnValue(null);

      const { result } = renderHook(() => useRevision());
      const href = result.current.withRev('/titles/17');

      expect(href).toBe('/titles/17');
    });

    it('appends ?rev= to href without query string', () => {
      mockGet.mockReturnValue('5');

      const { result } = renderHook(() => useRevision());
      const href = result.current.withRev('/titles/17');

      expect(href).toBe('/titles/17?rev=5');
    });

    it('appends &rev= to href with existing query string', () => {
      mockGet.mockReturnValue('5');

      const { result } = renderHook(() => useRevision());
      const href = result.current.withRev('/search?q=test');

      expect(href).toBe('/search?q=test&rev=5');
    });
  });
});
