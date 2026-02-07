export default function MainLayout({
  sidebar,
  children,
}: {
  sidebar?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-[calc(100vh-57px)]">
      {sidebar}
      <main className="flex-1 overflow-y-auto px-6 pb-6">
        <div className="pt-6">{children}</div>
      </main>
    </div>
  );
}
