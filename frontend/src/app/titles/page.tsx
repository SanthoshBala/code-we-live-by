import TitleList from '@/components/tree/TitleList';

export default function TitlesPage() {
  return (
    <main className="min-h-screen p-8">
      <div className="mx-auto max-w-4xl">
        <h1 className="mb-6 text-3xl font-bold">Browse the US Code</h1>
        <TitleList />
      </div>
    </main>
  );
}
