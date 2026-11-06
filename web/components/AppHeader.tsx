import Link from "next/link";
import { BackendStatus } from "./BackendStatus";

export function Logo() {
  return (
    <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden>
      <rect width="26" height="26" rx="6" fill="var(--accent)" />
      <rect x="5" y="13" width="2.6" height="8" rx="1.3" fill="var(--accent-ink)" />
      <rect x="9.6" y="6" width="2.6" height="15" rx="1.3" fill="var(--accent-ink)" />
      <rect x="14.2" y="10" width="2.6" height="11" rx="1.3" fill="var(--accent-ink)" />
      <rect x="18.8" y="15.5" width="2.6" height="5.5" rx="1.3" fill="var(--accent-ink)" />
    </svg>
  );
}

export function AppHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-bg/90 backdrop-blur supports-[backdrop-filter]:bg-bg/75">
      <div className="mx-auto flex h-14 max-w-[1680px] items-center gap-6 px-4 lg:px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <Logo />
          <span className="font-display text-[21px] font-bold tracking-wide text-ink-1 uppercase">PitchVision</span>
        </Link>
        <nav className="flex items-center gap-1 text-[13px]">
          <Link href="/" className="rounded-md px-2.5 py-1.5 text-ink-2 hover:bg-s2 hover:text-ink-1">
            Library
          </Link>
          <Link href="/analyze" className="rounded-md px-2.5 py-1.5 text-ink-2 hover:bg-s2 hover:text-ink-1">
            Analyse
          </Link>
          <Link href="/method" className="hidden rounded-md px-2.5 py-1.5 text-ink-2 hover:bg-s2 hover:text-ink-1 sm:inline">
            Method &amp; limits
          </Link>
        </nav>
        <div className="ml-auto">
          <BackendStatus />
        </div>
      </div>
    </header>
  );
}
