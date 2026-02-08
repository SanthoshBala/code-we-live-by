'use client';

import { usePathname } from 'next/navigation';
import MainLayout from '@/components/ui/MainLayout';
import Sidebar from '@/components/ui/Sidebar';
import TitleList from '@/components/tree/TitleList';
import type { TreeActivePath } from '@/lib/types';

function parseActivePath(pathname: string): TreeActivePath | undefined {
  // /titles/17/chapters/1/subchapters/A
  const match = pathname.match(
    /^\/titles\/(\d+)(?:\/chapters\/([^/]+)(?:\/subchapters\/([^/]+))?)?/
  );
  if (!match) return undefined;
  return {
    titleNumber: Number(match[1]),
    chapterNumber: match[2] || undefined,
    subchapterNumber: match[3] || undefined,
  };
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
