import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import QueryProvider from '@/components/QueryProvider';
import Header from '@/components/ui/Header';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'The Code We Live By',
  description: 'Explore the US Code like a software repository',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <QueryProvider>
          <Header />
          {children}
        </QueryProvider>
      </body>
    </html>
  );
}
