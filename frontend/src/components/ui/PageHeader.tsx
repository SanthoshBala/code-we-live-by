import type { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  subtitle?: ReactNode;
  badges?: ReactNode;
}

/** Shared page header with title, subtitle, and optional badges row. */
export default function PageHeader({
  title,
  subtitle,
  badges,
}: PageHeaderProps) {
  return (
    <header className="mb-6">
      <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
      {subtitle &&
        (typeof subtitle === 'string' ? (
          <p className="mt-1 text-lg text-gray-600">{subtitle}</p>
        ) : (
          subtitle
        ))}
      {badges && (
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
          {badges}
        </div>
      )}
    </header>
  );
}
