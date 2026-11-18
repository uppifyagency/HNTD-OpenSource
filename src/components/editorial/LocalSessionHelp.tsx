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
      lede="In locale non serve un account. Questo browser però non è ancora stato collegato: apri una volta il link che npm run local stampa nel terminale."
      footer={<>riprova: <a href="/dashboard" style={{ color: "var(--ink)", textDecoration: "underline", textUnderlineOffset: 3 }}>→ dashboard</a></>}
    >
      <ol className="mono" style={{ fontSize: 13, lineHeight: 1.9, paddingLeft: 18, margin: 0 }}>
        <li>guarda il terminale dove gira <code>npm run local</code></li>
        <li>apri il link <code>HNTD local: http://127.0.0.1:…/api/local-session?key=…</code></li>
        <li>se il link non c&apos;è: ferma, esegui <code>scripts/local/setup.sh</code>, rilancia</li>
      </ol>
    </EditorialAuth>
  );
}
