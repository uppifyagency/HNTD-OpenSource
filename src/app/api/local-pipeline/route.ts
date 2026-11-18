import { readFile } from "node:fs/promises";
import { NextRequest, NextResponse } from "next/server";
import { APP_MODE } from "@/lib/mode";
import { isLocalBrowser } from "@/lib/session/loopback";
import {
  WORKER_STATUS_PATH,
  checkGithubToken,
  isTokenShaped,
  saveGithubToken,
  type TokenProblem,
} from "@/lib/local/pipelineEnv";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// The worker rewrites its status every few seconds; older than this, it is not running.
const WORKER_STALE_MS = 30_000;

function guard(req: NextRequest): NextResponse | null {
  if (APP_MODE !== "local") return new NextResponse(null, { status: 404 });
  if (!isLocalBrowser(req)) {
    return NextResponse.json({ error: "open the link printed by npm run local" }, { status: 403 });
  }
  return null;
}

/** The local worker's status (scripts/local/worker.py): GitHub reachable, idle or running. */
export async function GET(req: NextRequest) {
  const denied = guard(req);
  if (denied) return denied;
  let status: { updatedAt?: number } = {};
  try {
    status = JSON.parse(await readFile(WORKER_STATUS_PATH, "utf8"));
  } catch {
    // no status file yet: the worker has not started
  }
  const alive = typeof status.updatedAt === "number" && Date.now() - status.updatedAt < WORKER_STALE_MS;
  return NextResponse.json({ ...status, alive }, { headers: { "Cache-Control": "no-store" } });
}

const TOKEN_PROBLEMS: Record<TokenProblem, string> = {
  rejected: "GitHub ha rifiutato il token.",
  unreachable: "GitHub non risponde, riprova tra poco.",
};

/**
 * Connect GitHub: check GitHub accepts the token, then store it where the pipeline reads it. The
 * worker rechecks the saved token and its status carries any warning to the banner.
 */
export async function POST(req: NextRequest) {
  const denied = guard(req);
  if (denied) return denied;
  const body = (await req.json().catch(() => null)) as { token?: unknown } | null;
  const token = typeof body?.token === "string" ? body.token.trim() : "";
  if (!isTokenShaped(token)) {
    return NextResponse.json({ error: "Non sembra un token GitHub." }, { status: 400 });
  }
  const verdict = await checkGithubToken(token);
  if (!verdict.ok) {
    return NextResponse.json({ error: TOKEN_PROBLEMS[verdict.problem] }, { status: 400 });
  }
  await saveGithubToken(token);
  return NextResponse.json({ login: verdict.login });
}
