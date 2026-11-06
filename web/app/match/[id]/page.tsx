import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { MatchWorkspace } from "@/components/MatchWorkspace";
import { getMatch, videoAvailable } from "@/lib/library.server";

export const dynamic = "force-dynamic";

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const b = await getMatch(id).catch(() => null);
  return { title: b?.title ?? "Match" };
}

export default async function MatchPage({ params }: Props) {
  const { id } = await params;
  const bundle = await getMatch(id);
  if (!bundle) notFound();
  const available = bundle.video ? await videoAvailable(bundle) : false;
  const videoUrl = available ? `/api/matches/${encodeURIComponent(bundle.id)}/files/${encodeURIComponent(bundle.video!)}` : null;
  // A bundle that names a video which isn't on disk (moved drive, dangling symlink) is a different message from
  // one built without a video at all.
  return <MatchWorkspace bundle={bundle} videoUrl={videoUrl} videoMissing={Boolean(bundle.video) && !available} />;
}
