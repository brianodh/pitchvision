import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto max-w-xl px-4 py-24 text-center">
      <p className="eyebrow">404</p>
      <h1 className="mt-2 font-display text-4xl font-bold tracking-wide text-ink-1 uppercase">Not in the library</h1>
      <p className="mt-3 text-sm text-ink-2">
        That match isn&apos;t in <code className="font-mono">web/data/matches/</code> on this machine.
      </p>
      <Link href="/" className="mt-6 inline-block rounded-md bg-accent px-4 py-2 text-sm font-semibold text-accent-ink">
        Back to the library
      </Link>
    </main>
  );
}
