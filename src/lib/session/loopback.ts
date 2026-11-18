import { createHmac, timingSafeEqual } from "node:crypto";
import type { NextRequest } from "next/server";

// Local mode serves one user on 127.0.0.1 and has no login, so its routes trust only requests a
// loopback page made. The Host check stops DNS rebinding (a page on another origin that resolves
// its own name to 127.0.0.1 still sends its own Host); the Origin check stops a cross-site page
// from posting to http://127.0.0.1 directly (a text/plain POST needs no CORS preflight).
const LOOPBACK_HOST = /^(127\.0\.0\.1|localhost|\[::1\])(:\d+)?$/;

export function isLoopbackRequest(headers: Headers): boolean {
  if (!LOOPBACK_HOST.test(headers.get("host") ?? "")) return false;
  const origin = headers.get("origin");
  if (origin === null) return true; // same-origin GETs and non-browser clients send none
  try {
    return LOOPBACK_HOST.test(new URL(origin).host);
  } catch {
    return false; // "null" and other opaque origins
  }
}

// A loopback check alone lets any local program in, the pipeline's sandboxed shell included: curl
// can send any header a browser sends. So the routes that sign a session or save the GitHub token
// also want the browser key, which a browser gets once from the link `npm run local` prints
// (GET /api/local-session?key=…) and keeps as an HttpOnly cookie. The key is derived from the
// session signing key in .env.local, which the sandbox cannot read.
export const BROWSER_KEY_COOKIE = "hntd_local";

/** What scripts/local/keys.mjs `browser-key` prints for the same key. */
export function browserKey(privateKeyPem: string): string {
  return createHmac("sha256", privateKeyPem).update("hntd-local-browser").digest("base64url");
}

export function isBrowserKey(value: string | null | undefined): boolean {
  const pem = process.env.LOCAL_AUTH_PRIVATE_KEY;
  if (!pem || !value) return false;
  const given = Buffer.from(value);
  const expected = Buffer.from(browserKey(pem));
  return given.length === expected.length && timingSafeEqual(given, expected);
}

/** A loopback request from a browser that holds the browser key. */
export function isLocalBrowser(req: NextRequest): boolean {
  return isLoopbackRequest(req.headers) && isBrowserKey(req.cookies.get(BROWSER_KEY_COOKIE)?.value);
}
