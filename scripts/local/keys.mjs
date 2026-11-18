// Local-mode signing key. Usage (from the repo root):
//   node scripts/local/keys.mjs init   writes .env.local with a fresh RSA key, unless it exists
//   node scripts/local/keys.mjs jwks   prints the public key of .env.local as a JWKS data: URI
//   node scripts/local/keys.mjs browser-key   prints the browser key (browserKey in src/lib/session/loopback.ts)
import { createHmac, createPrivateKey, createPublicKey, generateKeyPairSync } from "node:crypto";
import fs from "node:fs";
import { parse } from "dotenv";

const ENV_FILE = ".env.local";
const KEY_ID = "hntd-local-1"; // must match LOCAL_KEY_ID in src/lib/session/localToken.ts

function privateKeyPem() {
  const pem = parse(fs.readFileSync(ENV_FILE)).LOCAL_AUTH_PRIVATE_KEY;
  if (!pem) throw new Error(`LOCAL_AUTH_PRIVATE_KEY missing from ${ENV_FILE}`);
  return pem;
}

const cmd = process.argv[2];
if (cmd === "init") {
  if (fs.existsSync(ENV_FILE)) process.exit(0);
  const { privateKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
  const pem = privateKey.export({ type: "pkcs8", format: "pem" }).toString().trim();
  const lines = [
    "# Written by scripts/local/setup.sh. Local mode: no Clerk, no Stripe, local Convex.",
    "NEXT_PUBLIC_HNTD_MODE=local",
    "CONVEX_AGENT_MODE=anonymous",
    `LOCAL_AUTH_PRIVATE_KEY="${pem.replace(/\n/g, "\\n")}"`,
  ];
  fs.writeFileSync(ENV_FILE, lines.join("\n") + "\n", { mode: 0o600 });
  fs.chmodSync(ENV_FILE, 0o600); // mode above applies only when the file is new
  console.log(`wrote ${ENV_FILE}`);
} else if (cmd === "jwks") {
  const jwk = createPublicKey(createPrivateKey(privateKeyPem())).export({ format: "jwk" });
  const jwks = JSON.stringify({ keys: [{ ...jwk, kid: KEY_ID, alg: "RS256", use: "sig" }] });
  process.stdout.write(`data:text/plain;charset=utf-8;base64,${Buffer.from(jwks).toString("base64")}`);
} else if (cmd === "browser-key") {
  process.stdout.write(createHmac("sha256", privateKeyPem()).update("hntd-local-browser").digest("base64url"));
} else {
  console.error("usage: node scripts/local/keys.mjs init|jwks|browser-key");
  process.exit(2);
}
