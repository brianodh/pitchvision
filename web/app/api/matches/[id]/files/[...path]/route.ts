import { isValidId, resolveInMatch } from "@/lib/library.server";
import { serveFile } from "@/lib/serve-file.server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string; path: string[] }> };

async function handle(req: Request, { params }: Ctx) {
  const { id, path: parts } = await params;
  if (!isValidId(id)) return new Response("Not found", { status: 404 });
  const rel = parts.map(decodeURIComponent).join("/");
  const file = resolveInMatch(id, rel);
  if (!file) return new Response("Not found", { status: 404 });
  const isThumb = rel.startsWith("thumbs/");
  return serveFile(file, req, isThumb ? 3600 : 0);
}

export const GET = handle;
export const HEAD = handle;
