import { LOCAL_ISSUER } from "./localAuth";

// A push fails when this file reads an env var the deployment does not set, so the branch is
// picked by CLERK_JWT_ISSUER_DOMAIN alone, which every deployment sets. Cloud sets it to the
// Clerk domain and never reads LOCAL_AUTH_JWKS. scripts/local/setup.sh sets it to LOCAL_ISSUER
// and sets LOCAL_AUTH_JWKS (a data: URI) on the local backend only.
const issuerDomain = process.env.CLERK_JWT_ISSUER_DOMAIN;

export default {
  providers:
    issuerDomain === LOCAL_ISSUER
      ? [
          {
            type: "customJwt" as const,
            issuer: LOCAL_ISSUER,
            applicationID: "convex",
            jwks: process.env.LOCAL_AUTH_JWKS,
            algorithm: "RS256" as const,
          },
        ]
      : [{ domain: issuerDomain, applicationID: "convex" }],
};
