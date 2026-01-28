export default function Home() {
  return (
    <main className="min-h-screen p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold mb-4">The Code We Live By</h1>
        <p className="text-lg text-gray-600 mb-8">
          Explore the United States Code like a software repository. See who wrote
          each line, when it changed, and why.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <a
            href="/titles"
            className="block p-6 bg-white rounded-lg border border-gray-200 hover:border-primary-500 transition-colors"
          >
            <h2 className="text-xl font-semibold mb-2">Browse Titles</h2>
            <p className="text-gray-600">
              Explore all 54 titles of the US Code organized by subject matter.
            </p>
          </a>

          <a
            href="/search"
            className="block p-6 bg-white rounded-lg border border-gray-200 hover:border-primary-500 transition-colors"
          >
            <h2 className="text-xl font-semibold mb-2">Search</h2>
            <p className="text-gray-600">
              Find specific sections, laws, or text across the entire US Code.
            </p>
          </a>

          <a
            href="/laws"
            className="block p-6 bg-white rounded-lg border border-gray-200 hover:border-primary-500 transition-colors"
          >
            <h2 className="text-xl font-semibold mb-2">Recent Laws</h2>
            <p className="text-gray-600">
              See the latest Public Laws and what they changed in the Code.
            </p>
          </a>

          <a
            href="/analytics"
            className="block p-6 bg-white rounded-lg border border-gray-200 hover:border-primary-500 transition-colors"
          >
            <h2 className="text-xl font-semibold mb-2">Analytics</h2>
            <p className="text-gray-600">
              Visualize legislative activity patterns and trends over time.
            </p>
          </a>
        </div>
      </div>
    </main>
  );
}
