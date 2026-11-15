"use client";

export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main className="mx-auto max-w-xl px-4 py-24 text-center">
      <p className="eyebrow">Something broke</p>
      <h1 className="mt-2 font-display text-4xl font-bold tracking-wide text-ink-1 uppercase">This page failed to load</h1>
      <p className="mt-3 font-mono text-[12.5px] text-ink-2">{error.message}</p>
      <button type="button" onClick={reset} className="mt-6 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-accent-ink">
        Try again
      </button>
    </main>
  );
}
