export default function Sidebar({ children }: { children?: React.ReactNode }) {
    return (
        <aside className="hidden w-64 shrink-0 border-r border-gray-200 bg-gray-50 p-4 md:block">
            {children ?? (
                <p className="text-sm text-gray-500">
                    Select a title to browse
                </p>
            )}
        </aside>
    );
}
