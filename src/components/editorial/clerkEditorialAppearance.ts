import type { Appearance } from "@clerk/types";

/**
 * Deep editorial theming for Clerk's <SignIn>/<SignUp> — makes the live widget read like the
 * hand-built signup mockup (docs/hntd-redesign-v2/signup.html) while staying a real, working
 * auth widget. "Il widget Clerk non si reskina — gli si costruisce intorno": we hide Clerk's
 * own header (our editorial hero replaces it), strip the card chrome so the form sits flush on
 * the paper, turn social buttons into editorial ghost buttons, and make inputs underline-only
 * (border-bottom) like .field__input. The widget renders INSIDE .skin-editorial, so var(--…)
 * skin tokens resolve in `elements`; `variables` keep literal HSL (Clerk processes those).
 */
const MONO = "var(--font-geist-mono), ui-monospace, monospace";

export const clerkEditorialAppearance: Appearance = {
  variables: {
    colorPrimary: "hsl(150 59% 30%)",
    colorText: "hsl(0 0% 4%)",
    colorTextSecondary: "hsl(0 0% 38%)",
    colorBackground: "hsl(42 31% 94%)",
    colorInputBackground: "transparent",
    colorInputText: "hsl(0 0% 4%)",
    colorDanger: "hsl(0 60% 42%)",
    fontFamily: MONO,
    borderRadius: "0",
  },
  elements: {
    rootBox: { width: "100%" },
    // flush on the paper — no card, no border, no shadow (our hero is the header)
    cardBox: { boxShadow: "none", border: "none", borderRadius: "0", width: "100%" },
    card: { boxShadow: "none", background: "transparent", border: "none", padding: "0" },
    header: { display: "none" },
    // social → editorial ghost buttons
    socialButtonsBlockButton: {
      border: "1px solid var(--rule-2)", borderRadius: "0", background: "transparent",
      boxShadow: "none", height: "44px", fontFamily: MONO, color: "var(--ink)",
    },
    socialButtonsBlockButtonText: { fontFamily: MONO, fontSize: "14px" },
    dividerLine: { background: "var(--rule-2)" },
    dividerText: { fontFamily: MONO, color: "var(--dim)", letterSpacing: "0.3em", fontSize: "12px" },
    // labels + underline-only inputs (like .field__input)
    formFieldLabel: { fontFamily: MONO, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--dim)", fontSize: "12px" },
    formFieldInput: {
      border: "0", borderBottom: "1px solid var(--rule)", borderRadius: "0", background: "transparent",
      padding: "8px 2px", fontFamily: MONO, fontSize: "15px", color: "var(--ink)", boxShadow: "none",
    },
    formFieldInputShowPasswordButton: { color: "var(--dim)" },
    formFieldHintText: { fontFamily: MONO, color: "var(--dim)", fontSize: "12px" },
    formFieldErrorText: { fontFamily: MONO, fontSize: "12px" },
    // primary CTA → accent green, sharp, flush
    formButtonPrimary: {
      background: "var(--ed-accent)", borderRadius: "0", boxShadow: "none",
      fontFamily: MONO, textTransform: "none", height: "46px", fontSize: "14px",
    },
    footer: { background: "transparent" },
    footerActionText: { fontFamily: MONO, color: "var(--dim)", fontSize: "12px" },
    footerActionLink: { fontFamily: MONO, color: "var(--ed-accent)" },
    identityPreviewText: { fontFamily: MONO },
    formResendCodeLink: { color: "var(--ed-accent)", fontFamily: MONO },
  },
};
