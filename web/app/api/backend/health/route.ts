import { checkHealth } from "@/lib/backend.server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// Reports readiness and limits. Deliberately never includes the backend URL or token.
export async function GET() {
  return Response.json(await checkHealth(), { headers: { "Cache-Control": "no-store" } });
}
