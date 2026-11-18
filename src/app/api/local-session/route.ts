import { NextRequest, NextResponse } from "next/server";
import { APP_MODE } from "@/lib/mode";
import { signLocalToken } from "@/lib/session/localToken";
import { isLoopbackRequest } from "@/lib/session/loopback";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  if (APP_MODE !== "local") return new NextResponse(null, { status: 404 });
  if (!isLoopbackRequest(req.headers)) {
    return NextResponse.json({ error: "local session is served on loopback only" }, { status: 403 });
  }
  const pem = process.env.LOCAL_AUTH_PRIVATE_KEY;
  if (!pem) {
    return NextResponse.json({ error: "LOCAL_AUTH_PRIVATE_KEY missing: run scripts/local/setup.sh" }, { status: 500 });
  }
  return NextResponse.json(signLocalToken(pem, Date.now()), { headers: { "Cache-Control": "no-store" } });
}
