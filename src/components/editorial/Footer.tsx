import type { ReactNode } from "react";

/**
 * Editorial footer / colophon. Styling in editorial.css (.foot*). Source: index.html.
 */
export type FootColumn = { title: string; links: { label: string; href: string }[] };

export type FooterProps = {
  colophon: ReactNode;
  columns: FootColumn[];
  bottomLeft: ReactNode;
  bottomRight: ReactNode;
};

export function Footer({ colophon, columns, bottomLeft, bottomRight }: FooterProps) {
  return (
    <footer className="foot wrap">
      <div className="foot__cols">
        <div className="foot__col">{colophon}</div>
        {columns.map((col, i) => (
          <div key={i} className="foot__col">
            <div className="foot__col-title">{col.title}</div>
            <ul>
              {col.links.map((l, j) => (
                <li key={j}>
                  <a href={l.href}>{l.label}</a>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="foot__bottom">
        <span>{bottomLeft}</span>
        <span>{bottomRight}</span>
      </div>
    </footer>
  );
}
