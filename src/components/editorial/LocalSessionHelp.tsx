import { EditorialAuth } from "@/components/editorial/EditorialAuth";

/**
 * /sign-in and /sign-up in local mode. There is no account to sign in to: the dashboard signs in
 * the local user by itself. Reaching this page means the local session failed, so say how to fix it
 * (a redirect to /dashboard would loop, since the dashboard sends signed-out visitors here).
 */
export function LocalSessionHelp() {
  return (
    <EditorialAuth
      kicker="modalità locale"
      title={<>Nessun login.<br /><span className="serif-it">Sei già dentro.</span></>}
      lede="In locale non serve un account: la dashboard ti riconosce da sola. Se sei finito qui, la sessione locale non è partita."
      footer={<>riprova: <a href="/dashboard" style={{ color: "var(--ink)", textDecoration: "underline", textUnderlineOffset: 3 }}>→ dashboard</a></>}
    >
      <ol className="mono" style={{ fontSize: 13, lineHeight: 1.9, paddingLeft: 18, margin: 0 }}>
        <li>ferma <code>npm run local</code></li>
        <li>esegui <code>scripts/local/setup.sh</code></li>
        <li>rilancia <code>npm run local</code></li>
      </ol>
    </EditorialAuth>
  );
}
