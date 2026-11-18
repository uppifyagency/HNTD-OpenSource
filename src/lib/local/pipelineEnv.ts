// Local mode only. The pipeline's env file (skill/scripts/.env, gitignored, mode 600) holds the
// local Convex URL, its secret and, once connected, GH_TOKEN: scripts/local/worker.py passes it to
// claude and every `gh` call. scripts/local/lib.sh (write_skill_env) writes the same file.
import { chmod, readFile, rename, writeFile } from "node:fs/promises";
import path from "node:path";

export const SKILL_ENV_PATH = path.join(process.cwd(), "skill", "scripts", ".env");
export const WORKER_STATUS_PATH = path.join(process.cwd(), ".convex", "hntd-worker.json");

// GitHub tokens (classic, fine-grained and OAuth) use only these characters, so a
// token that passes cannot smuggle a newline or a second variable into the env file.
const TOKEN_SHAPE = /^[A-Za-z0-9_]{20,255}$/;

export function isTokenShaped(token: string): boolean {
  return TOKEN_SHAPE.test(token);
}

/** The env file text with `key` set to `value`, every other line kept as it was. */
export function withEnvVar(text: string, key: string, value: string): string {
  const lines = text.split("\n").filter((line, i, all) => line !== "" || i < all.length - 1);
  const kept = lines.filter((line) => !line.startsWith(`${key}=`));
  return [...kept, `${key}=${value}`].join("\n") + "\n";
}

export async function saveGithubToken(token: string): Promise<void> {
  if (!isTokenShaped(token)) throw new Error("not a GitHub token");
  const text = await readFile(SKILL_ENV_PATH, "utf8");
  const tmp = `${SKILL_ENV_PATH}.tmp`;
  await writeFile(tmp, withEnvVar(text, "GH_TOKEN", token), { mode: 0o600 });
  await chmod(tmp, 0o600); // a leftover tmp keeps its old mode
  await rename(tmp, SKILL_ENV_PATH);
}

export type TokenProblem = "rejected" | "unreachable";
export type TokenVerdict =
  | { ok: true; login: string }
  | { ok: false; problem: TokenProblem };

/**
 * Whether GitHub accepts a token, and as whom. Any token it accepts is saved; the worker
 * (scripts/local/github_token.py) judges whether it could write and warns in its status.
 */
export async function checkGithubToken(token: string): Promise<TokenVerdict> {
  let res: Response;
  try {
    res = await fetch("https://api.github.com/user", {
      headers: { Authorization: `Bearer ${token}`, "User-Agent": "hntd-local", Accept: "application/vnd.github+json" },
      cache: "no-store",
      signal: AbortSignal.timeout(15_000),
    });
  } catch {
    return { ok: false, problem: "unreachable" };
  }
  if (res.status >= 500) return { ok: false, problem: "unreachable" };
  if (res.status !== 200) return { ok: false, problem: "rejected" };
  const body = (await res.json().catch(() => null)) as { login?: unknown } | null;
  if (typeof body?.login !== "string" || body.login === "") return { ok: false, problem: "rejected" };
  return { ok: true, login: body.login };
}
