import { SignIn } from "@clerk/nextjs";
import { EditorialAuth } from "@/components/editorial/EditorialAuth";
import { clerkEditorialAppearance } from "@/components/editorial/clerkEditorialAppearance";
import { LocalSessionHelp } from "@/components/editorial/LocalSessionHelp";
import { APP_MODE } from "@/lib/mode";

/**
 * Live sign-in — editorial split (Clerk widget themed via clerkEditorialAppearance inside
 * HNTD's own chrome, no longer a bare default widget). Mirrors the /sign-up shell.
 */
export default function SignInPage() {
  if (APP_MODE === "local") return <LocalSessionHelp />;
  return (
    <EditorialAuth
      kicker="sign in"
      title={<>Bentornato.<br /><span className="serif-it">Riprendi.</span></>}
      lede="Accedi per riprendere le tue ricerche, la shortlist e la pipeline."
      footer={<>non hai un account? <a href="/sign-up" style={{ color: "var(--ink)", textDecoration: "underline", textUnderlineOffset: 3 }}>→ crea account</a></>}
    >
      <SignIn appearance={clerkEditorialAppearance} />
    </EditorialAuth>
  );
}
