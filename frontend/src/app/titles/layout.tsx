'use client';

import { usePathname } from 'next/navigation';
import MainLayout from '@/components/ui/MainLayout';
import Sidebar from '@/components/ui/Sidebar';
import TitleList from '@/components/tree/TitleList';
import type { TreeActivePath } from '@/lib/types';

function parseActivePath(pathname: string): TreeActivePath | undefined {
  // /titles/17/chapters/1/subchapters/A
  const chapterMatch = pathname.match(
    /^\/titles\/(\d+)\/chapters\/([^/]+)(?:\/subchapters\/([^/]+))?/
  );
  if (chapterMatch) {
    return {
      titleNumber: Number(chapterMatch[1]),
      chapterNumber: chapterMatch[2],
      subchapterNumber: chapterMatch[3] || undefined,
    };
  }

  // /titles/18/part/III or /titles/10/subtitle/A/part/I
  const groupMatch = pathname.match(/^\/titles\/(\d+)((?:\/[^/]+\/[^/]+)+)$/);
  if (groupMatch) {
    const segments = groupMatch[2].slice(1).split('/');
    const groupPath: { type: string; number: string }[] = [];
    for (let i = 0; i < segments.length - 1; i += 2) {
      groupPath.push({ type: segments[i], number: segments[i + 1] });
    }
    return { titleNumber: Number(groupMatch[1]), groupPath };
  }

  // /titles/17
  const titleMatch = pathname.match(/^\/titles\/(\d+)/);
  if (titleMatch) {
    return { titleNumber: Number(titleMatch[1]) };
  }

  return undefined;
}

export default function TitlesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const activePath = parseActivePath(pathname);

  return (
    <MainLayout
      sidebar={
        <Sidebar>
          <TitleList activePath={activePath} />
        </Sidebar>
      }
    >
      {children}
    </MainLayout>
  );
}
