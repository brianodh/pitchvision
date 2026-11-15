import Link from "next/link";
import { formatDuration } from "@/lib/derive";
import { listMatches } from "@/lib/library.server";

export const dynamic = "force-dynamic";

export default async function LibraryPage() {
  const { matches, broken } = await listMatches();
  const demos = matches.filter((m) => m.source === "demo");
  const uploads = matches.filter((m) => m.source === "upload");

  return (
    <main className="mx-auto w-full max-w-[1680px] px-4 pt-8 pb-16 lg:px-6">
      <section className="mb-10 max-w-3xl">
        <p className="eyebrow">Match library · runs on this machine</p>
        <h1 className="mt-2 font-display text-[40px] leading-[0.98] font-bold tracking-wide text-ink-1 uppercase sm:text-[52px]">
          Never scrub through 90 minutes again.
        </h1>
        <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-ink-2">
          PitchVision finds the ball events in match video — passes, carries, crosses, headers, shots, throw-ins, blocks,
          tackles — and puts them on a timeline you can search. Click any event and the video is there.
        </p>
      </section>

      {matches.length === 0 ? (
        <EmptyLibrary />
      ) : (
        <>
          {demos.length > 0 && <MatchGrid title="Pre-analysed matches" note="Work fully offline — no backend needed." items={demos} />}
          {uploads.length > 0 && <MatchGrid title="Your analyses" note="Saved from live uploads." items={uploads} />}
        </>
      )}

      {broken.length > 0 && (
        <div className="mt-8 rounded-lg border border-danger/40 bg-danger/5 p-4 text-sm">
          <p className="font-medium text-ink-1">Some folders in the library could not be read</p>
          <ul className="mt-2 space-y-1 font-mono text-[12px] text-ink-2">
            {broken.map((b) => (
              <li key={b.id}>
                data/matches/{b.id}: {b.error}
              </li>
            ))}
          </ul>
        </div>
      )}
    </main>
  );
}

function MatchGrid({
  title,
  note,
  items,
}: {
  title: string;
  note: string;
  items: Awaited<ReturnType<typeof listMatches>>["matches"];
}) {
  return (
    <section className="mb-10">
      <header className="mb-3 flex items-baseline gap-3">
        <h2 className="font-display text-xl font-semibold tracking-wide text-ink-1 uppercase">{title}</h2>
        <span className="text-[12.5px] text-ink-3">{note}</span>
      </header>
      <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {items.map((m) => (
          <li key={m.id}>
            <Link
              href={`/match/${m.id}`}
              className="group block overflow-hidden rounded-[10px] border border-line bg-s1 transition-colors hover:border-line-strong"
            >
              <div className="relative aspect-[16/8] bg-s2">
                {m.firstThumb ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={`/api/matches/${m.id}/files/${m.firstThumb}`}
                    alt=""
                    className="h-full w-full object-cover opacity-80 transition-opacity group-hover:opacity-100"
                  />
                ) : (
                  <div className="hatch absolute inset-0" />
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-s1 via-s1/10 to-transparent" />
                {!m.hasVideo && (
                  <span className="absolute top-3 left-3 rounded bg-bg/85 px-2 py-0.5 text-[11px] text-warn">
                    Video file not found
                  </span>
                )}
              </div>
              <div className="p-4 pt-1">
                <h3 className="font-display text-[22px] leading-tight font-semibold tracking-wide text-ink-1 uppercase">
                  {m.title}
                </h3>
                {m.subtitle && <p className="mt-0.5 text-[13px] text-ink-3">{m.subtitle}</p>}
                <dl className="mt-3 flex gap-5 font-mono text-[12px] tabular">
                  <div>
                    <dt className="sr-only">Events</dt>
                    <dd className="text-ink-1">
                      {m.eventCount.toLocaleString()} <span className="text-ink-3">events</span>
                    </dd>
                  </div>
                  <div>
                    <dt className="sr-only">Duration</dt>
                    <dd className="text-ink-2">{formatDuration(m.duration_s)}</dd>
                  </div>
                  <div>
                    <dt className="sr-only">Engine</dt>
                    <dd className="text-ink-3">{m.engine}</dd>
                  </div>
                </dl>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

function EmptyLibrary() {
  return (
    <section className="panel max-w-3xl p-6">
      <h2 className="font-display text-2xl font-semibold tracking-wide text-ink-1 uppercase">No matches in the library yet</h2>
      <p className="mt-2 text-sm text-ink-2">
        The library lives in <code className="font-mono text-ink-1">web/data/matches/</code> on this machine. Build the
        pre-analysed demo from a v9 timeline and your local copy of the video:
      </p>
      <pre className="scroll-quiet mt-4 overflow-x-auto rounded-md border border-line bg-bg p-4 font-mono text-[12px] leading-relaxed text-ink-2">
{`python backend/scripts/build_demo.py \\
  --timeline out_v9/timeline.json \\
  --video "/path/to/2019-10-01 - Stoke City - Huddersfield Town/720p.mp4" \\
  --title "Stoke City vs Huddersfield Town" \\
  --subtitle "EFL Championship · 1 Oct 2019"`}
      </pre>
      <p className="mt-4 text-[13px] text-ink-3">
        No timeline yet? Run <code className="font-mono">model/scripts/spot_video_v9.py</code>, or the full-match cell in{" "}
        <code className="font-mono">backend/colab_server.ipynb</code>, then reload this page. Footage and thumbnails stay on
        this machine — SoccerNet data is licensed for non-commercial research with no redistribution.
      </p>
    </section>
  );
}
