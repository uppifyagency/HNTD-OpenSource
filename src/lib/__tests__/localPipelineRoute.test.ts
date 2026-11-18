import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/mode", () => ({ APP_MODE: "local" }));
vi.mock("@/lib/session/loopback", () => ({ isLocalBrowser: () => true }));
vi.mock("@/lib/local/pipelineEnv", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/local/pipelineEnv")>()),
  saveGithubToken: vi.fn(async () => {}),
}));

const { POST } = await import("@/app/api/local-pipeline/route");
const { saveGithubToken } = await import("@/lib/local/pipelineEnv");

const TOKEN = "t".repeat(40);

function connect() {
  return POST(new NextRequest("http://127.0.0.1:3117/api/local-pipeline", {
    method: "POST",
    body: JSON.stringify({ token: TOKEN }),
  }));
}

// GitHub's answer to GET /user: `scopes` is the X-OAuth-Scopes header, null for no header.
function githubAnswers(scopes: string | null) {
  const headers = new Headers();
  if (scopes !== null) headers.set("X-OAuth-Scopes", scopes);
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ login: "octocat" }), { status: 200, headers })));
}

describe("POST /api/local-pipeline", () => {
  beforeEach(() => vi.mocked(saveGithubToken).mockClear());
  afterEach(() => vi.unstubAllGlobals());

  it.each(["", "repo", null])("saves any token GitHub accepts (scopes header %s)", async (scopes) => {
    githubAnswers(scopes);
    const res = await connect();
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ login: "octocat" });
    expect(saveGithubToken).toHaveBeenCalledWith(TOKEN);
  });

  it("refuses a token GitHub rejects", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("", { status: 401 })));
    const res = await connect();
    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({ error: "GitHub ha rifiutato il token." });
    expect(saveGithubToken).not.toHaveBeenCalled();
  });
});
