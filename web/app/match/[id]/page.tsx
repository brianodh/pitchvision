import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { MatchWorkspace } from "@/components/MatchWorkspace";
import { parseClassesParam, parseTimeParam } from "@/lib/filter-url";
import { getMatch, videoAvailable } from "@/lib/library.server";

export const dynamic = "force-dynamic";

type Props = {
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const b = await getMatch(id).catch(() => null);
  return { title: b?.title ?? "Match" };
}

export default async function MatchPage({ params, searchParams }: Props) {
  const { id } = await params;
  const query = await searchParams;
  const bundle = await getMatch(id);
  if (!bundle) notFound();
  const available = bundle.video ? await videoAvailable(bundle) : false;
  const videoUrl = available ? `/api/matches/${encodeURIComponent(bundle.id)}/files/${encodeURIComponent(bundle.video!)}` : null;
  // A bundle that names a video which isn't on disk (moved drive, dangling symlink) is a different message from
  // one built without a video at all.
  // The filter is resolved here, on the server, so a shared `?classes=shot` link renders filtered from the first
  // byte — not "All" until hydration catches up.
  return (
    <MatchWorkspace
      bundle={bundle}
      videoUrl={videoUrl}
      videoMissing={Boolean(bundle.video) && !available}
      initialClasses={parseClassesParam(query.classes)}
      initialTime={parseTimeParam(query.t)}
    />
  );
}
