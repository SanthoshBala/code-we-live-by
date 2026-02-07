import MainLayout from '@/components/ui/MainLayout';
import Sidebar from '@/components/ui/Sidebar';
import TitleList from '@/components/tree/TitleList';
import SectionViewer from '@/components/viewer/SectionViewer';

interface SectionPageProps {
  params: { titleNumber: string; sectionNumber: string };
}

export default function SectionPage({ params }: SectionPageProps) {
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
      <SectionViewer titleNumber={titleNumber} sectionNumber={sectionNumber} />
    </MainLayout>
  );
}
