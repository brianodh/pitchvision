"use client";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { classFromSlug, classSlug } from "@/lib/classes";
import { eventMix, formatDuration, keyPassages, tempo, type Passage } from "@/lib/derive";
import { RELIABILITY_SOURCE, reliabilityApplies } from "@/lib/reliability";
import { createTimeStore } from "@/lib/time-store";
import type { EventClass, MatchBundle, MatchEvent } from "@/lib/types";
import { ClassFilter } from "./ClassFilter";
import { EventList } from "./EventList";
import { EventMix } from "./EventMix";
import { KeyPassages } from "./KeyPassages";
import { ReliabilityNote } from "./ReliabilityNote";
import { TempoChart } from "./TempoChart";
import { Timeline, type FocusRequest } from "./Timeline";
import { VideoPlayer, type PlayerHandle } from "./VideoPlayer";

const LEAD_OPTIONS = [0, 2, 5];
const LEAD_KEY = "pv.leadIn";

function readInitialClasses(): Set<EventClass> {
  if (typeof window === "undefined") return new Set();
  const raw = new URLSearchParams(window.location.search).get("classes");
  if (!raw) return new Set();
  return new Set(raw.split(",").map(classFromSlug).filter((c): c is EventClass => c !== null));
}

export function MatchWorkspace({
  bundle,
  videoUrl,
  videoMissing = false,
}: {
  bundle: MatchBundle;
  videoUrl: string | null;
  videoMissing?: boolean;
}) {
  const store = useMemo(() => createTimeStore(), []);
  const player = useRef<PlayerHandle>(null);
  const [selected, setSelected] = useState<Set<EventClass>>(() => new Set());
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);
  const [leadIn, setLeadIn] = useState(2);
  const [focus, setFocus] = useState<FocusRequest | null>(null);
  const reliabilityOn = reliabilityApplies(bundle.engine);

  // URL <-> filter, so "every cross" is a link you can send: /match/<id>?classes=cross
  useEffect(() => {
    setSelected(readInitialClasses());
    const t = Number(new URLSearchParams(window.location.search).get("t"));
    if (Number.isFinite(t) && t > 0) setTimeout(() => player.current?.seek(t), 50);
    try {
      const raw = window.localStorage.getItem(LEAD_KEY);
      if (raw !== null && LEAD_OPTIONS.includes(Number(raw))) setLeadIn(Number(raw));
    } catch {
      /* storage unavailable: keep the default */
    }
  }, []);
  useEffect(() => {
    const url = new URL(window.location.href);
    if (selected.size) url.searchParams.set("classes", [...selected].map(classSlug).join(","));
    else url.searchParams.delete("classes");
    window.history.replaceState(null, "", url);
  }, [selected]);

  const filtered = useMemo(
    () => (selected.size ? bundle.events.filter((e) => selected.has(e.class)) : bundle.events),
    [bundle.events, selected],
  );
  const counts = useMemo(() => {
    const m = new Map<EventClass, number>();
    for (const e of bundle.events) m.set(e.class, (m.get(e.class) ?? 0) + 1);
    return m;
  }, [bundle.events]);
  const bins = useMemo(() => tempo(bundle, 60), [bundle]);
  const passages = useMemo(() => keyPassages(bundle, { windowS: 120, k: 5 }), [bundle]);
  const mix = useMemo(() => eventMix(bundle.events), [bundle.events]);
  const analysedS = bundle.analysed.end_s - bundle.analysed.start_s;

  const thumbUrl = useCallback(
    (e: MatchEvent) => (e.thumb ? `/api/matches/${encodeURIComponent(bundle.id)}/files/${e.thumb}` : null),
    [bundle.id],
  );

  const pick = useCallback(
    (e: MatchEvent) => {
      setSelectedEventId(e.id);
      player.current?.seek(e.t - leadIn);
    },
    [leadIn],
  );
  const seekTime = useCallback((t: number) => player.current?.seek(t), []);
  const openPassage = useCallback((p: Passage) => {
    setFocus({ start: p.start, end: p.end, nonce: Date.now() });
    player.current?.seek(p.start);
  }, []);

  const toggleClass = (c: EventClass) =>
    setSelected((s) => {
      const n = new Set(s);
      if (n.has(c)) n.delete(c);
      else n.add(c);
      return n;
    });

  // Keyboard: space play/pause, ←/→ previous/next event in the current filter, shift+←/→ ±5 s.
  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      const el = ev.target as HTMLElement | null;
      if (el && (el.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName))) return;
      if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
      if (ev.key === " " && el?.tagName !== "BUTTON" && el?.tagName !== "VIDEO") {
        ev.preventDefault();
        player.current?.toggle();
      } else if (ev.key === "ArrowRight" || ev.key === "ArrowLeft") {
        if (el?.tagName === "VIDEO") return; // the video element handles its own arrows
        ev.preventDefault();
        const now = store.get();
        if (ev.shiftKey) {
          player.current?.seek(now + (ev.key === "ArrowRight" ? 5 : -5));
          return;
        }
        const ref = now + leadIn;
        const target =
          ev.key === "ArrowRight"
            ? filtered.find((e) => e.t > ref + 0.3)
            : [...filtered].reverse().find((e) => e.t < ref - 0.3);
        if (target) pick(target);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [filtered, leadIn, pick, store]);

  return (
    <main className="mx-auto w-full max-w-[1680px] px-4 pt-4 pb-16 lg:px-6">
      {/* match header */}
      <div className="mb-4 flex flex-wrap items-end gap-x-6 gap-y-3">
        <div className="min-w-0">
          <Link href="/" className="eyebrow hover:text-ink-2">
            ← Library
          </Link>
          <h1 className="mt-1 font-display text-[28px] leading-[1.05] font-bold tracking-wide text-ink-1 uppercase sm:text-[34px]">
            {bundle.title}
          </h1>
          {bundle.subtitle && <p className="mt-1 text-sm text-ink-2">{bundle.subtitle}</p>}
        </div>
        <dl className="ml-auto flex flex-wrap gap-x-6 gap-y-2">
          <Meta label="Detected events" value={bundle.events.length.toLocaleString()} />
          <Meta label="Analysed" value={formatDuration(analysedS)} />
          <Meta label="Model" value={`${bundle.engine} · ≥ ${bundle.threshold}`} title={bundle.model} />
          <Meta label="Source" value={bundle.source === "demo" ? "Demo · local" : "Your upload"} />
        </dl>
      </div>

      {/* player + list */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(320px,400px)]">
        <div className="min-w-0">
          <VideoPlayer ref={player} src={videoUrl} store={store} duration={bundle.duration_s} missing={videoMissing} />
        </div>
        <aside className="panel relative flex h-[420px] flex-col overflow-hidden sm:h-[520px] lg:h-auto lg:min-h-[420px]">
          <div className="flex flex-col lg:absolute lg:inset-0">
            <div className="flex items-center justify-between gap-2 px-3 pt-3">
              <h2 className="font-display text-lg font-semibold tracking-wide text-ink-1 uppercase">Events</h2>
              <label className="flex items-center gap-1.5 text-[11px] text-ink-3">
                Lead-in
                <select
                  value={leadIn}
                  onChange={(e) => {
                    const v = Number(e.target.value);
                    setLeadIn(v);
                    try {
                      window.localStorage.setItem(LEAD_KEY, String(v));
                    } catch {
                      /* ignore */
                    }
                  }}
                  className="rounded border border-line bg-s2 px-1.5 py-0.5 font-mono text-[11px] text-ink-2"
                  aria-label="Seconds of build-up before each event when jumping to it"
                >
                  {LEAD_OPTIONS.map((o) => (
                    <option key={o} value={o}>
                      {o} s
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <EventList
              events={filtered}
              totalCount={bundle.events.length}
              store={store}
              threshold={bundle.threshold}
              reliabilityOn={reliabilityOn}
              selectedEventId={selectedEventId}
              thumbUrl={thumbUrl}
              onPick={pick}
              emptyMessage={bundle.events.length ? "No events of the selected classes." : "The model detected no events in this video."}
            />
          </div>
        </aside>
      </div>

      {/* filter */}
      <div className="mt-4 mb-3">
        <ClassFilter
          counts={counts}
          selected={selected}
          reliabilityOn={reliabilityOn}
          onToggle={toggleClass}
          onOnly={(c) => setSelected(new Set([c]))}
          onClear={() => setSelected(new Set())}
        />
      </div>

      <Timeline
        bundle={bundle}
        selected={selected}
        store={store}
        tempoBins={bins}
        passages={passages}
        reliabilityOn={reliabilityOn}
        selectedEventId={selectedEventId}
        focus={focus}
        thumbUrl={thumbUrl}
        onSeekTime={seekTime}
        onPickEvent={pick}
      />

      {/* overview */}
      <div className="mt-4 grid grid-cols-1 items-start gap-4 md:grid-cols-2 xl:grid-cols-12">
        <Panel
          className="md:col-span-2 xl:col-span-7"
          title="Match tempo"
          kicker="Detected events per minute"
          aside={<TempoSummary bins={bins} />}
        >
          <TempoChart bins={bins} onSeek={(t) => player.current?.seek(t)} />
        </Panel>
        <Panel className="xl:col-span-5" title="Key passages" kicker="Densest two-minute windows · look here first">
          <KeyPassages passages={passages} onOpen={openPassage} tooShort={analysedS < 120} />
        </Panel>
        <Panel className="xl:col-span-7" title="Event mix" kicker="Detected events by class">
          <EventMix rows={mix} reliabilityOn={reliabilityOn} selected={selected} onPick={(c) => setSelected(new Set([c]))} />
        </Panel>
        <Panel className="xl:col-span-5" title="How far to trust this" kicker={reliabilityOn ? "Validated per class" : "Not validated for this engine"}>
          <ReliabilityNote engine={bundle.engine} />
        </Panel>
      </div>

      <p className="mt-6 text-[11.5px] text-ink-4">
        Event counts are detections, not ground truth. At threshold {RELIABILITY_SOURCE.threshold}, about{" "}
        {Math.round(RELIABILITY_SOURCE.falsePositiveShare * 100)}% of detections on the validation match had no true event
        of the same class within one second. The first and last ~{Math.round(bundle.analysed.start_s)} s of a clip have no
        full scoring window, so the model cannot detect events there; they are hatched on the timeline.
      </p>
    </main>
  );
}

function Meta({ label, value, title }: { label: string; value: string; title?: string }) {
  return (
    <div title={title}>
      <dt className="eyebrow">{label}</dt>
      <dd className="mt-0.5 font-mono text-[14px] tabular text-ink-1">{value}</dd>
    </div>
  );
}

function Panel({
  title,
  kicker,
  aside,
  className = "",
  children,
}: {
  title: string;
  kicker?: string;
  aside?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <section className={`panel p-4 ${className}`}>
      <header className="mb-3 flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2 className="font-display text-lg font-semibold tracking-wide text-ink-1 uppercase">{title}</h2>
        {kicker && <span className="text-[12px] text-ink-3">{kicker}</span>}
        {aside && <div className="ml-auto">{aside}</div>}
      </header>
      {children}
    </section>
  );
}

function TempoSummary({ bins }: { bins: ReturnType<typeof tempo> }) {
  const valid = bins.filter((b) => b.perMinute !== null);
  if (!valid.length) return null;
  const busiest = valid.reduce((a, b) => ((b.perMinute ?? 0) > (a.perMinute ?? 0) ? b : a));
  const quietest = valid.reduce((a, b) => ((b.perMinute ?? 0) < (a.perMinute ?? 0) ? b : a));
  return (
    <span className="flex gap-4 font-mono text-[11px] tabular text-ink-3">
      <span>
        busiest <b className="font-medium text-ink-1">{Math.round(busiest.start / 60)}&apos;</b>{" "}
        <span className="text-ink-2">({busiest.count})</span>
      </span>
      <span>
        quietest <b className="font-medium text-ink-1">{Math.round(quietest.start / 60)}&apos;</b>{" "}
        <span className="text-ink-2">({quietest.count})</span>
      </span>
    </span>
  );
}
