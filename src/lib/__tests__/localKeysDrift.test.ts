// The local-mode trust chain is spread over a shell script, a Node script and TypeScript.
// These tests run the real scripts so a rename on one side fails here, not at login.
import { execFileSync } from "node:child_process";
import { createPublicKey, createVerify } from "node:crypto";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { parse } from "dotenv";
import { afterAll, describe, expect, it } from "vitest";
import { LOCAL_ISSUER } from "../../../convex/localAuth";
import { signLocalToken } from "@/lib/session/localToken";
import { browserKey } from "@/lib/session/loopback";

const ROOT = path.resolve(__dirname, "../../..");
const KEYS = path.join(ROOT, "scripts/local/keys.mjs");

describe("scripts/local/keys.mjs and signLocalToken", () => {
  const dir = mkdtempSync(path.join(tmpdir(), "hntd-keys-"));
  afterAll(() => rmSync(dir, { recursive: true, force: true }));

  it("a token signed with the init key verifies against the published JWKS", () => {
    execFileSync("node", [KEYS, "init"], { cwd: dir });
    const dataUri = execFileSync("node", [KEYS, "jwks"], { cwd: dir }).toString();
    const jwks = JSON.parse(Buffer.from(dataUri.split("base64,")[1], "base64").toString());
    const pem = parse(readFileSync(path.join(dir, ".env.local"))).LOCAL_AUTH_PRIVATE_KEY;

    const [header, payload, signature] = signLocalToken(pem, Date.now()).token.split(".");
    const { kid } = JSON.parse(Buffer.from(header, "base64url").toString());
    const jwk = jwks.keys.find((k: { kid: string }) => k.kid === kid);
    expect(jwk, `no JWKS key with kid ${kid}`).toBeDefined();

    const ok = createVerify("RSA-SHA256")
      .update(`${header}.${payload}`)
      .verify(createPublicKey({ key: jwk, format: "jwk" }), Buffer.from(signature, "base64url"));
    expect(ok).toBe(true);
  });

  it("the browser key run.sh prints is the one the routes accept", () => {
    execFileSync("node", [KEYS, "init"], { cwd: dir });
    const pem = parse(readFileSync(path.join(dir, ".env.local"))).LOCAL_AUTH_PRIVATE_KEY;
    expect(execFileSync("node", [KEYS, "browser-key"], { cwd: dir }).toString()).toBe(browserKey(pem));
  });
});

describe("scripts/local/setup.sh", () => {
  it("sets CLERK_JWT_ISSUER_DOMAIN to LOCAL_ISSUER", () => {
    const setup = readFileSync(path.join(ROOT, "scripts/local/setup.sh"), "utf8");
    const set = [...setup.matchAll(/convex env set CLERK_JWT_ISSUER_DOMAIN (\S+)/g)].map((m) => m[1]);
    expect(set).toEqual([LOCAL_ISSUER]);
  });
});
