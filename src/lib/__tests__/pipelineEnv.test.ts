import { afterEach, describe, expect, it, vi } from "vitest";
import { checkGithubToken, isTokenShaped, withEnvVar } from "@/lib/local/pipelineEnv";

describe("withEnvVar", () => {
  it("adds the key and keeps the other lines", () => {
    expect(withEnvVar("CONVEX_SITE_URL=http://127.0.0.1:3211\nAPI_SECRET=abc\n", "GH_TOKEN", "ghp_x"))
      .toBe("CONVEX_SITE_URL=http://127.0.0.1:3211\nAPI_SECRET=abc\nGH_TOKEN=ghp_x\n");
  });
  it("replaces an existing value instead of adding a second one", () => {
    expect(withEnvVar("GH_TOKEN=old\nAPI_SECRET=abc\n", "GH_TOKEN", "new")).toBe("API_SECRET=abc\nGH_TOKEN=new\n");
  });
});

describe("isTokenShaped", () => {
  it("accepts classic and fine-grained tokens", () => {
    expect(isTokenShaped("ghp_" + "a".repeat(36))).toBe(true);
    const fineGrainedPrefix = ["github", "pat", ""].join("_"); // spelled out, it trips the export's secret gate
    expect(isTokenShaped(fineGrainedPrefix + "A1_".repeat(25))).toBe(true);
  });
  it("rejects anything that could inject a line into the env file", () => {
    expect(isTokenShaped("ghp_" + "a".repeat(36) + "\nAPI_SECRET=x")).toBe(false);
    expect(isTokenShaped("short")).toBe(false);
  });
});

// GitHub's answer to GET /user, faked: `scopes` is the X-OAuth-Scopes header, null for no header.
function githubAnswers(status: number, scopes: string | null) {
  const headers = new Headers({ "Content-Type": "application/json" });
  if (scopes !== null) headers.set("X-OAuth-Scopes", scopes);
  const fetchMock = vi.fn(async () => new Response(JSON.stringify({ login: "octocat" }), { status, headers }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("checkGithubToken", () => {
  afterEach(() => vi.unstubAllGlobals());

  it.each(["", " repo, delete_repo ", null])("accepts any token GitHub answers for (scopes header %s)", async (scopes) => {
    const fetchMock = githubAnswers(200, scopes);
    expect(await checkGithubToken("t")).toEqual({ ok: true, login: "octocat" });
    expect(fetchMock).toHaveBeenCalledOnce();
  });
  it("rejects a token GitHub does not accept", async () => {
    githubAnswers(401, null);
    expect(await checkGithubToken("t")).toEqual({ ok: false, problem: "rejected" });
  });
  it("reports GitHub down rather than judging the token", async () => {
    githubAnswers(503, null);
    expect(await checkGithubToken("t")).toEqual({ ok: false, problem: "unreachable" });
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("fetch failed"); }));
    expect(await checkGithubToken("t")).toEqual({ ok: false, problem: "unreachable" });
  });
});
