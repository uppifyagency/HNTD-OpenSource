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
