import Link from 'next/link';

export default function Home() {
  return (
    <main className="min-h-screen p-8">
      <div className="mx-auto max-w-4xl">
        <h1 className="mb-4 text-4xl font-bold">The Code We Live By</h1>
        <p className="mb-8 text-lg text-gray-600">
          Explore the United States Code like a software repository. See who
          wrote each line, when it changed, and why.
        </p>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <Link
            href="/titles"
            className="block rounded-lg border border-gray-200 bg-white p-6 transition-colors hover:border-primary-500"
          >
            <h2 className="mb-2 text-xl font-semibold">Browse Titles</h2>
            <p className="text-gray-600">
              Explore all 54 titles of the US Code organized by subject matter.
            </p>
          </Link>

          <div className="block rounded-lg border border-gray-200 bg-white p-6 opacity-50">
            <h2 className="mb-2 text-xl font-semibold">Search</h2>
            <p className="text-gray-600">
              Find specific sections, laws, or text across the entire US Code.
            </p>
            <span className="mt-2 inline-block text-xs text-gray-400">
              Coming soon
            </span>
          </div>

          <div className="block rounded-lg border border-gray-200 bg-white p-6 opacity-50">
            <h2 className="mb-2 text-xl font-semibold">Recent Laws</h2>
            <p className="text-gray-600">
              See the latest Public Laws and what they changed in the Code.
            </p>
            <span className="mt-2 inline-block text-xs text-gray-400">
              Coming soon
            </span>
          </div>

          <div className="block rounded-lg border border-gray-200 bg-white p-6 opacity-50">
            <h2 className="mb-2 text-xl font-semibold">Analytics</h2>
            <p className="text-gray-600">
              Visualize legislative activity patterns and trends over time.
            </p>
            <span className="mt-2 inline-block text-xs text-gray-400">
              Coming soon
            </span>
          </div>
        </div>
      </div>
    </main>
  );
}
