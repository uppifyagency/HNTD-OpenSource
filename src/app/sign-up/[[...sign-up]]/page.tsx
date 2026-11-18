import { SignUp } from "@clerk/nextjs";
import { EditorialAuth } from "@/components/editorial/EditorialAuth";
import { clerkEditorialAppearance } from "@/components/editorial/clerkEditorialAppearance";
import { LocalSessionHelp } from "@/components/editorial/LocalSessionHelp";
import { APP_MODE } from "@/lib/mode";

/**
 * Live sign-up — editorial split (the Clerk widget lives inside HNTD's own chrome, themed via
 * clerkEditorialAppearance, no longer a bare default widget). Migrate of /editorial/signup, de-faked.
 */
export default function SignUpPage() {
  if (APP_MODE === "local") return <LocalSessionHelp />;
  return (
    <EditorialAuth
      kicker="new account"
      title={<>Crea il tuo<br /><span className="serif-it">account.</span></>}
      lede="Trenta secondi, niente carta. Tra meno di 35 minuti avrai davanti il primo dossier — e capirai perché chi lo usa non torna più a LinkedIn."
      footer={<>già un account? <a href="/sign-in" style={{ color: "var(--ink)", textDecoration: "underline", textUnderlineOffset: 3 }}>→ sign in</a></>}
    >
      <SignUp appearance={clerkEditorialAppearance} />
    </EditorialAuth>
  );
}
