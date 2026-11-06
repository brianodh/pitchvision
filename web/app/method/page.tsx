import type { Metadata } from "next";
import { TierIcon } from "@/components/ReliabilityMark";
import { CLASS_META, familyColor } from "@/lib/classes";
import { RELIABILITY, RELIABILITY_SOURCE, TIER_LABEL, formatRatio, reliabilitySentence, tierOf } from "@/lib/reliability";

export const metadata: Metadata = { title: "Method & limits" };

// Every number on this page is a measurement from model/README_v8.md, README_v9.md or README_playerid.md.
// Don't add one that isn't.

const DEGRADATION = [
  { cond: "Heavy compression (CRF 40)", delta: "−42.7%" },
  { cond: "Blur", delta: "−17.3%" },
  { cond: "Low resolution", delta: "−11.7%" },
  { cond: "Zoomed framing", delta: "−1.4%" },
  { cond: "Darker lighting", delta: "+0.4%" },
  { cond: "Mild camera shake", delta: "+3.6%" },
];

export default function MethodPage() {
  return (
    <main className="mx-auto w-full max-w-[1100px] px-4 pt-8 pb-20 lg:px-6">
      <p className="eyebrow">Method &amp; limits</p>
      <h1 className="mt-2 font-display text-[40px] leading-none font-bold tracking-wide text-ink-1 uppercase">
        What PitchVision measures — and what it won&apos;t claim
      </h1>
      <p className="mt-4 max-w-3xl text-[15px] leading-relaxed text-ink-2">
        PitchVision spots twelve kinds of ball event in broadcast footage and timestamps each one. Everything else on the
        match page — tempo, event mix, key passages — is counted from those timestamps and nothing more. Each figure below
        was measured; where we couldn&apos;t measure something well enough, it isn&apos;t in the product.
      </p>

      <Section title="How reliable is each class?">
        <p className="mb-4 max-w-3xl text-sm text-ink-2">
          Validated on the {RELIABILITY_SOURCE.match}, {RELIABILITY_SOURCE.model}, threshold {RELIABILITY_SOURCE.threshold},
          matched against SoccerNet&apos;s hand annotations: {RELIABILITY_SOURCE.detected.toLocaleString()} detected against{" "}
          {RELIABILITY_SOURCE.annotated.toLocaleString()} annotated. The ratio is <b className="text-ink-1">detected ÷ true count</b>.
          It is not accuracy — a class at 1.00× could still be half false alarms cancelling half misses.
        </p>
        <div className="scroll-quiet overflow-x-auto rounded-lg border border-line">
          <table className="w-full min-w-[640px] text-left text-[13px]">
            <thead className="bg-s2 text-ink-3">
              <tr>
                <th className="px-3 py-2 font-medium">Class</th>
                <th className="px-3 py-2 text-right font-medium">Annotated</th>
                <th className="px-3 py-2 text-right font-medium">Detected</th>
                <th className="px-3 py-2 text-right font-medium">Det ÷ true</th>
                <th className="px-3 py-2 font-medium">What it means</th>
              </tr>
            </thead>
            <tbody>
              {[...CLASS_META]
                .sort((a, b) => RELIABILITY[b.cls].actual - RELIABILITY[a.cls].actual)
                .map((m) => {
                  const r = RELIABILITY[m.cls];
                  const tier = tierOf(m.cls);
                  return (
                    <tr key={m.cls} className={`border-t border-line ${tier === "unreliable" ? "text-ink-3" : "text-ink-2"}`}>
                      <td className="px-3 py-2">
                        <span className="inline-flex items-center gap-2">
                          <span className="h-2 w-2 rounded-full" style={{ background: familyColor(m.cls) }} />
                          <span className={tier === "unreliable" ? "" : "text-ink-1"}>{m.label}</span>
                          {m.label.toUpperCase() !== m.source && <span className="font-mono text-[10.5px] text-ink-4">{m.source}</span>}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right font-mono tabular">{r.actual}</td>
                      <td className="px-3 py-2 text-right font-mono tabular">{r.detected}</td>
                      <td className="px-3 py-2 text-right font-mono tabular text-ink-1">{formatRatio(r.ratio)}</td>
                      <td className="px-3 py-2">
                        <span className="flex items-start gap-2">
                          <span className="mt-[3px]">
                            <TierIcon tier={tier} />
                          </span>
                          <span>
                            <span className="text-ink-1">{TIER_LABEL[tier]}.</span> {reliabilitySentence(m.cls)}
                          </span>
                        </span>
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
        <ul className="mt-4 max-w-3xl space-y-2 text-sm text-ink-2">
          <li>
            <b className="text-ink-1">False alarms:</b> about {Math.round(RELIABILITY_SOURCE.falsePositiveShare * 100)}% of all
            detections had no true event of the same class within one second.
          </li>
          <li>
            <b className="text-ink-1">Tiers:</b> fewer than 20 annotated examples, or a count off by more than ~1.75× either way,
            is marked unreliable and shown muted. A ratio outside 0.80–1.25 is marked “check by eye”. The tiers are a
            presentation rule; the table is the measurement.
          </li>
          <li>
            <b className="text-ink-1">Scores</b> are raw model outputs, not calibrated probabilities, and the 0.5 threshold was
            not tuned. The app shows them only as a relative bar.
          </li>
        </ul>
      </Section>

      <Section title="Where it can't see">
        <ul className="max-w-3xl space-y-2 text-sm text-ink-2">
          <li>
            The model scores each moment from a 19.5-second window centred on it, so the first and last ~9.5 seconds of every
            clip have no full window and are not analysed. They are hatched on the timeline.
          </li>
          <li>Trained and validated on 224p multi-camera broadcast footage. Phone, sideline and non-16:9 video are untested.</li>
        </ul>
      </Section>

      <Section title="Upload quality matters more than anything else">
        <p className="mb-3 max-w-3xl text-sm text-ink-2">
          Measured on a 10-minute held-out slice, one degradation at a time (change in mAP@1 vs the clean original):
        </p>
        <div className="grid max-w-xl grid-cols-[1fr_auto] gap-x-6 gap-y-1 text-[13px]">
          {DEGRADATION.map((d) => (
            <div key={d.cond} className="contents">
              <span className="text-ink-2">{d.cond}</span>
              <span className={`text-right font-mono tabular ${d.delta.startsWith("−4") ? "text-warn" : "text-ink-1"}`}>{d.delta}</span>
            </div>
          ))}
        </div>
        <p className="mt-3 max-w-3xl text-sm text-ink-2">
          Video forwarded through messaging apps or re-uploaded to social platforms is recompressed hard. Upload the
          original file.
        </p>
      </Section>

      <Section title="What PitchVision deliberately does not show">
        <dl className="grid max-w-4xl gap-4 sm:grid-cols-2">
          <NoShow title="Possession, team splits, pass accuracy">
            Team attribution from kit colour measured 42.0% on 1,591 matched events using the frame-centre player and 65.0% on
            648 using the ball. At 65%, a true 55/45 split reads as roughly 51.5% ± 6% — unreadable. Thumbnails are shown
            unlabelled: you can see the kit and attribute it yourself, correctly.
          </NoShow>
          <NoShow title="Player names or per-player tallies">
            Jersey-number OCR returned a correct number on about 1% of events, and tracking fragments into 25,477 IDs across a
            full match, so no identity survives a camera cut.
          </NoShow>
          <NoShow title="Shots on target, cards, offsides, corners">
            None of these is among the twelve event classes, and none can be derived from them.
          </NoShow>
          <NoShow title="Confidence percentages">
            Scores aren&apos;t calibrated probabilities, so a “91% confident” label would be invented precision.
          </NoShow>
        </dl>
      </Section>

      <Section title="Model and speed">
        <p className="max-w-3xl text-sm text-ink-2">
          Engine v9: T-DEED&apos;s frozen per-frame representation with PitchVision&apos;s multi-scale head. On two held-out
          broadcast matches it scores mAP@1 0.673 and 0.652 (five seeds; an event counts only if placed within one second).
          It runs at roughly 0.6× real time on a T4 GPU — a 2-minute clip takes about 75 seconds, a full match about an hour —
          which is why live uploads are capped and full matches are pre-analysed.
        </p>
      </Section>
    </main>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-12">
      <h2 className="mb-4 font-display text-2xl font-semibold tracking-wide text-ink-1 uppercase">{title}</h2>
      {children}
    </section>
  );
}

function NoShow({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="panel p-4">
      <dt className="font-medium text-ink-1">{title}</dt>
      <dd className="mt-1.5 text-[13px] leading-relaxed text-ink-2">{children}</dd>
    </div>
  );
}
