// The local-mode identity. A token with this issuer is accepted only by a deployment whose
// LOCAL_AUTH_JWKS env var is set (convex/auth.config.ts), which production never sets.
// Convex requires the issuer to look like a URL; .invalid is reserved and never resolves.
export const LOCAL_ISSUER = "https://local.hntd.invalid";

export const LOCAL_USER = {
  subject: "local-user",
  email: "local@hntd.local",
  name: "Local user",
} as const;
