"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="it">
      <body className="bg-black text-white font-mono flex items-center justify-center min-h-screen">
        <div className="max-w-lg text-center space-y-4 p-8">
          <h1 className="text-2xl font-bold">Something went wrong</h1>
          <p className="text-gray-400 text-sm">{error.message}</p>
          {error.digest && (
            <p className="text-gray-600 text-xs">Digest: {error.digest}</p>
          )}
          <button
            onClick={reset}
            className="mt-4 px-4 py-2 bg-white text-black rounded hover:bg-gray-200 transition-colors text-sm"
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
