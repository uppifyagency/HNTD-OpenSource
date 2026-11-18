/**
 * Read a user-facing message out of a rejected Convex call.
 *
 * WHY THIS EXISTS: a PRODUCTION Convex deployment redacts `err.message` for an uncaught error to
 * a generic `"Server Error"` with no stack trace, and only an application error's `data` payload
 * survives (docs.convex.dev/functions/error-handling). So `err.message` — the obvious thing to
 * show — is exactly the thing that is empty in the only environment that matters. Any mutation
 * whose failure the user is supposed to read must throw `ConvexError({ code, message })`, and
 * every caller must come through here.
 *
 * Returns null when there is no message worth showing, so the caller supplies its own fallback
 * rather than printing "Server Error" at somebody.
 */
export function convexErrorMessage(err: unknown): string | null {
  const data = (err as { data?: unknown } | null | undefined)?.data;

  // The shape we throw: ConvexError({ code, message }).
  if (data && typeof data === "object" && typeof (data as { message?: unknown }).message === "string") {
    const message = (data as { message: string }).message.trim();
    if (message !== "") return message;
  }
  // ConvexError("a bare string") is also legal.
  if (typeof data === "string" && data.trim() !== "") return data.trim();

  // Dev deployments (and non-Convex failures) still carry a real message. Suppress Convex's
  // redaction placeholder so it never reaches a user.
  const message = err instanceof Error ? err.message.trim() : "";
  if (message === "" || /server error/i.test(message)) return null;
  return message;
}
