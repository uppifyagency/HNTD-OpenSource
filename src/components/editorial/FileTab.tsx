/**
 * File-tab ID chip (e.g. "07:dossier.candidate").
 * Styling lives in editorial.css (.file-tab*). Source of truth: candidate.html.
 */
export type FileTabProps = {
  id: string;
  ghost?: boolean;
};

export function FileTab({ id, ghost = false }: FileTabProps) {
  return <span className={`file-tab${ghost ? " file-tab--ghost" : ""}`}>{id}</span>;
}
