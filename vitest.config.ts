import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  test: {
    // Only our unit tests — docs/design-references contains vendored bun:test suites
    include: ["src/**/*.test.{ts,tsx}"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
