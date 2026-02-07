import { notFound } from 'next/navigation';
import MainLayout from '@/components/ui/MainLayout';
import Sidebar from '@/components/ui/Sidebar';
import TitleList from '@/components/tree/TitleList';
import NotesViewer from '@/components/viewer/NotesViewer';

const VALID_FILES = new Set([
  'EDITORIAL_NOTES',
  'STATUTORY_NOTES',
  'HISTORICAL_NOTES',
]);

interface NoteFilePageProps {
  params: { titleNumber: string; sectionNumber: string; file: string };
}

export default function NoteFilePage({ params }: NoteFilePageProps) {
  if (!VALID_FILES.has(params.file)) {
    notFound();
  }

  const titleNumber = Number(params.titleNumber);
  const sectionNumber = params.sectionNumber;

  return (
    <MainLayout
      sidebar={
        <Sidebar>
          <TitleList compact />
        </Sidebar>
      }
    >
      <NotesViewer
        titleNumber={titleNumber}
        sectionNumber={sectionNumber}
        file={params.file}
      />
    </MainLayout>
  );
}
