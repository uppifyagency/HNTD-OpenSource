import { createVerify, generateKeyPairSync } from "node:crypto";
import { describe, expect, it } from "vitest";
import { LOCAL_KEY_ID, signLocalToken } from "@/lib/session/localToken";

const { privateKey, publicKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
const pem = privateKey.export({ type: "pkcs8", format: "pem" }).toString();
const decode = (part: string) => JSON.parse(Buffer.from(part, "base64url").toString());

describe("signLocalToken", () => {
  const now = Date.UTC(2026, 10, 18, 12);
  const { token, expiresAt } = signLocalToken(pem, now);
  const [header, payload, signature] = token.split(".");

  it("signs RS256 with the key id the JWKS carries", () => {
    expect(decode(header)).toEqual({ alg: "RS256", typ: "JWT", kid: LOCAL_KEY_ID });
    const ok = createVerify("RSA-SHA256").update(`${header}.${payload}`).verify(publicKey, Buffer.from(signature, "base64url"));
    expect(ok).toBe(true);
  });

  it("carries the claims Convex checks and getOrCreateUser reads", () => {
    const claims = decode(payload);
    expect(claims).toMatchObject({ iss: "https://local.hntd.invalid", aud: "convex", sub: "local-user", email_verified: true });
    expect(claims.exp - claims.iat).toBe(3600);
    expect(expiresAt).toBe(claims.exp * 1000);
  });
});
