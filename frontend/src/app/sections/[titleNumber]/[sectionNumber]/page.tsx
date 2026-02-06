import MainLayout from '@/components/ui/MainLayout';
import Sidebar from '@/components/ui/Sidebar';
import TitleList from '@/components/tree/TitleList';

interface SectionPageProps {
  params: { titleNumber: string; sectionNumber: string };
}

export default function SectionPage({ params }: SectionPageProps) {
  const { titleNumber, sectionNumber } = params;

  return (
    <MainLayout
      sidebar={
        <Sidebar>
          <TitleList compact />
        </Sidebar>
      }
    >
      <div>
        <h1 className="mb-4 text-2xl font-bold">
          {titleNumber} U.S.C. &sect; {sectionNumber}
        </h1>
        <p className="text-gray-500">Section viewer coming in Task 1A.7.</p>
      </div>
    </MainLayout>
  );
}
