import { Fragment } from "react";

/**
 * Infinite CSS marquee strip (trusted-by). Styling in editorial.css (.marquee*).
 * Pure CSS animation — no JS. Source: index.html.
 */
export type MarqueeProps = {
  items: string[];
};

export function Marquee({ items }: MarqueeProps) {
  // Duplicate the sequence so the -50% translate loops seamlessly.
  const seq = [...items, ...items];
  return (
    <div className="marquee" aria-hidden="true">
      <div className="marquee__track">
        {seq.map((item, i) => (
          <Fragment key={i}>
            <span>{item}</span>
            <span>·</span>
          </Fragment>
        ))}
      </div>
    </div>
  );
}
