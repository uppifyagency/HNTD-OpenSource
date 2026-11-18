import { describe, expect, it } from "vitest";
import { isLoopbackRequest } from "@/lib/session/loopback";

const req = (headers: Record<string, string>) => isLoopbackRequest(new Headers(headers));

describe("isLoopbackRequest", () => {
  it("accepts a loopback page on any loopback name", () => {
    expect(req({ host: "127.0.0.1:3000", origin: "http://127.0.0.1:3000" })).toBe(true);
    expect(req({ host: "localhost:3000", origin: "http://localhost:3000" })).toBe(true);
    expect(req({ host: "[::1]:3000" })).toBe(true);
  });
  it("rejects a cross-site page posting to the loopback server", () => {
    expect(req({ host: "127.0.0.1:3000", origin: "https://evil.example" })).toBe(false);
    expect(req({ host: "127.0.0.1:3000", origin: "null" })).toBe(false);
  });
  it("rejects a rebound DNS name", () => {
    expect(req({ host: "evil.example:3000", origin: "http://evil.example:3000" })).toBe(false);
    expect(req({ host: "127.0.0.1.evil.example" })).toBe(false);
  });
});
