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
  const videoUrl =
    bundle.video && (await videoAvailable(bundle))
      ? `/api/matches/${encodeURIComponent(bundle.id)}/files/${encodeURIComponent(bundle.video)}`
      : null;
  return <MatchWorkspace bundle={bundle} videoUrl={videoUrl} />;
}
