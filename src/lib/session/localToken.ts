import { createSign } from "node:crypto";
import { LOCAL_ISSUER, LOCAL_USER } from "../../../convex/localAuth";

// Must match the "kid" that scripts/local/keys.mjs writes into LOCAL_AUTH_JWKS.
export const LOCAL_KEY_ID = "hntd-local-1";
const TOKEN_TTL_S = 60 * 60;

const b64url = (data: string | Buffer) => Buffer.from(data).toString("base64url");

export function signLocalToken(privateKeyPem: string, nowMs: number): { token: string; expiresAt: number } {
  const iat = Math.floor(nowMs / 1000);
  const exp = iat + TOKEN_TTL_S;
  const header = b64url(JSON.stringify({ alg: "RS256", typ: "JWT", kid: LOCAL_KEY_ID }));
  const payload = b64url(
    JSON.stringify({
      iss: LOCAL_ISSUER,
      aud: "convex",
      sub: LOCAL_USER.subject,
      email: LOCAL_USER.email,
      email_verified: true,
      name: LOCAL_USER.name,
      iat,
      exp,
    }),
  );
  const signature = createSign("RSA-SHA256").update(`${header}.${payload}`).sign(privateKeyPem);
  return { token: `${header}.${payload}.${b64url(signature)}`, expiresAt: exp * 1000 };
}
