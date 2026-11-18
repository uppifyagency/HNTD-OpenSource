import { NextRequest, NextResponse } from "next/server";
import { APP_MODE } from "@/lib/mode";
import { signLocalToken } from "@/lib/session/localToken";
import { BROWSER_KEY_COOKIE, isBrowserKey, isLocalBrowser, isLoopbackRequest } from "@/lib/session/loopback";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const BROWSER_KEY_MAX_AGE_S = 400 * 24 * 60 * 60; // the longest a browser keeps a cookie

/**
 * With ?key=: the link `npm run local` prints. Stores the browser key as a cookie and opens the
 * dashboard. Without: a session token for the page, only for a browser that holds the key.
 */
export async function GET(req: NextRequest) {
  if (APP_MODE !== "local") return new NextResponse(null, { status: 404 });
  if (!isLoopbackRequest(req.headers)) {
    return NextResponse.json({ error: "local session is served on loopback only" }, { status: 403 });
  }
  const pem = process.env.LOCAL_AUTH_PRIVATE_KEY;
  if (!pem) {
    return NextResponse.json({ error: "LOCAL_AUTH_PRIVATE_KEY missing: run scripts/local/setup.sh" }, { status: 500 });
  }
  const key = req.nextUrl.searchParams.get("key");
  if (key !== null) {
    if (!isBrowserKey(key)) return NextResponse.json({ error: "link not valid" }, { status: 403 });
    // Relative: req.url names 127.0.0.1 as localhost, a different cookie host.
    const res = new NextResponse(null, { status: 303, headers: { Location: "/dashboard" } });
    res.cookies.set(BROWSER_KEY_COOKIE, key, {
      httpOnly: true,
      sameSite: "strict",
      path: "/",
      maxAge: BROWSER_KEY_MAX_AGE_S,
    });
    return res;
  }
  if (!isLocalBrowser(req)) {
    return NextResponse.json({ error: "open the link printed by npm run local" }, { status: 403 });
  }
  return NextResponse.json(signLocalToken(pem, Date.now()), { headers: { "Cache-Control": "no-store" } });
}
