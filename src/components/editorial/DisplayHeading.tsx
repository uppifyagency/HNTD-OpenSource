import type { CSSProperties, ReactNode } from "react";

/**
 * Mono display headline. Styling in editorial.css (.h-xl/.h-lg/.h-md/.h-sm/.h-xs).
 * Source of truth: index.html headlines.
 */
export type DisplayHeadingProps = {
  as?: "h1" | "h2" | "h3";
  size?: "xl" | "lg" | "md" | "sm" | "xs";
  className?: string;
  style?: CSSProperties;
  children: ReactNode;
};

export function DisplayHeading({
  as = "h2",
  size = "lg",
  className = "",
  style,
  children,
}: DisplayHeadingProps) {
  const Tag = as;
  return (
    <Tag className={`h-${size}${className ? ` ${className}` : ""}`} style={style}>
      {children}
    </Tag>
  );
}
