export default function MainLayout({
  sidebar,
  children,
}: {
  sidebar?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-[calc(100vh-57px)]">
      {sidebar}
      <main className="flex-1 p-6">{children}</main>
    </div>
  );
}
