import { clerkMiddleware } from "@clerk/nextjs/server";
import type { NextRequest, NextResponse } from "next/server";
import { APP_MODE } from "@/lib/mode";

type Handler = (request: NextRequest) => NextResponse | Promise<NextResponse>;

// Cloud: Clerk must see every request so auth() works in route handlers. Local: no Clerk at all.
export function withSession(handler: Handler) {
  return APP_MODE === "local" ? handler : clerkMiddleware((_auth, request) => handler(request));
}
