import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { withSession } from "@/lib/session/middleware";

// Pages served on the marketing domain (hntd.it)
const LANDING_PATHS = new Set(["/", "/privacy", "/terms", "/gdpr"]);

const MARKETING_HOST = "hntd.it";
const APP_HOST = "app.hntd.it";

function isMarketingHost(host: string): boolean {
  // Match hntd.it and www.hntd.it (strip port for local dev)
  const h = host.split(":")[0];
  return h === MARKETING_HOST || h === `www.${MARKETING_HOST}`;
}

function isAppHost(host: string): boolean {
  return host.split(":")[0] === APP_HOST;
}

export default withSession(async (request: NextRequest) => {
  const host = request.headers.get("host") ?? "";
  const { pathname } = request.nextUrl;

  // ── Marketing domain: hntd.it ──
  if (isMarketingHost(host)) {
    // Allow landing-related paths through
    if (LANDING_PATHS.has(pathname)) {
      return NextResponse.next();
    }
    // Everything else → redirect to app subdomain
    const url = new URL(pathname + request.nextUrl.search, `https://${APP_HOST}`);
    return NextResponse.redirect(url, 308);
  }

  // ── App domain: app.hntd.it ──
  if (isAppHost(host)) {
    // Root → dashboard
    if (pathname === "/") {
      const url = request.nextUrl.clone();
      url.pathname = "/dashboard";
      return NextResponse.redirect(url, 308);
    }
    // Block landing-only pages on app subdomain (except /)
    if (LANDING_PATHS.has(pathname) && pathname !== "/") {
      const url = new URL(pathname, `https://${MARKETING_HOST}`);
      return NextResponse.redirect(url, 308);
    }
  }

  // ── Local dev / preview deploys: no hostname routing ──
  return NextResponse.next();
});

export const config = {
  matcher: [
    // Skip Next.js internals and all static files, unless found in search params
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    // Always run for API routes
    "/(api|trpc)(.*)",
  ],
};
