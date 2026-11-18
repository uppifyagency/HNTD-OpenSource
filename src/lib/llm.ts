import { spawn } from "node:child_process";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import Anthropic from "@anthropic-ai/sdk";
import { APP_MODE } from "@/lib/mode";

const MODEL = "claude-haiku-4-5-20251001";
const CLI_TIMEOUT_MS = 120_000;

/** The model replied, but not with JSON. Callers map this to their own "could not interpret" result. */
export class LlmJsonError extends Error {}

/**
 * One prompt in, the model's reply parsed as JSON out. Throws LlmJsonError when the reply is not JSON.
 * ANTHROPIC_API_KEY set → Anthropic SDK. Local mode without a key → the installed `claude` CLI,
 * which runs on the user's own subscription. Cloud without a key → the SDK throws, as before.
 */
export async function completeJson(prompt: string, maxTokens: number): Promise<unknown> {
  const text =
    APP_MODE === "local" && !process.env.ANTHROPIC_API_KEY
      ? await viaClaudeCli(prompt)
      : await viaSdk(prompt, maxTokens);
  return parseJsonReply(text);
}

export function parseJsonReply(text: string): unknown {
  try {
    return JSON.parse(stripCodeFence(text));
  } catch {
    throw new LlmJsonError(`model reply is not JSON: ${text.slice(0, 200)}`);
  }
}

async function viaSdk(prompt: string, maxTokens: number): Promise<string> {
  const response = await new Anthropic().messages.create({
    model: MODEL,
    max_tokens: maxTokens,
    messages: [{ role: "user", content: prompt }],
  });
  return response.content[0].type === "text" ? response.content[0].text : "{}";
}

// The prompt carries GitHub profile text, which must not be able to act: no tools, no MCP. The run
// also must not pick up the user's own Claude Code setup: --safe-mode drops CLAUDE.md, hooks and
// installed plugins, --setting-sources project with an empty temp cwd skips the user's settings
// (and the plugins they enable), --disable-slash-commands drops skills. Not --bare: it forces an API key.
const CLI_ARGS = [
  "-p", "--output-format", "json", "--model", MODEL,
  "--tools", "", "--strict-mcp-config", "--no-session-persistence",
  "--safe-mode", "--setting-sources", "project", "--disable-slash-commands",
];

async function viaClaudeCli(prompt: string): Promise<string> {
  const cwd = await mkdtemp(path.join(tmpdir(), "hntd-llm-"));
  try {
    return await runClaude(prompt, cwd);
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
}

function runClaude(prompt: string, cwd: string): Promise<string> {
  // CLAUDECODE marks a parent Claude Code session; the CLI refuses to start nested under it.
  const env = { ...process.env };
  delete env.CLAUDECODE;
  return new Promise((resolve, reject) => {
    const child = spawn("claude", CLI_ARGS, { cwd, env, stdio: ["pipe", "pipe", "pipe"], timeout: CLI_TIMEOUT_MS });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (d) => (stdout += d));
    child.stderr.on("data", (d) => (stderr += d));
    child.on("error", (err) => reject(new Error(`could not run the claude CLI (is Claude Code installed?): ${err.message}`)));
    child.on("close", (code) => {
      try {
        const out = JSON.parse(stdout) as { is_error?: boolean; result?: string };
        if (code !== 0 || out.is_error || typeof out.result !== "string") throw new Error(out.result ?? "no result");
        resolve(out.result);
      } catch (err) {
        reject(new Error(`claude CLI failed (exit ${code}): ${String(err)} ${stderr.slice(0, 300)}`));
      }
    });
    child.stdin.end(prompt);
  });
}

// Models sometimes wrap JSON in a ```json fence even when asked not to.
export function stripCodeFence(text: string): string {
  const m = text.trim().match(/^```(?:json)?\s*\n([\s\S]*?)\n?```$/);
  return m ? m[1] : text.trim();
}
