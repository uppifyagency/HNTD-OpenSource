import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Not TypeScript sources: without these `npm run lint` walks Python virtualenvs and
    // dies of a V8 heap OOM, so the gate CLAUDE.md documents never actually ran.
    ".venv*/**",
    "skill/**",
    "e2e-test/**",
    "paidwait-landing/**",
    "docs/**",
  ]),
]);

export default eslintConfig;
