"""Local pipeline worker: runs pending searches from the dashboard, one at a time.

Started by `npm run local` (scripts/local/run.sh) with the pipeline's venv python. Each loop it
asks the LOCAL backend for pending tasks, checks that the pipeline can reach GitHub, claims the
oldest task (pending -> processing, refused if another run took it first) with a new claim id,
and runs `claude -p "/github-hr run --task <id>"` in the repo with HNTD_CLAIM_ID=<claim id>, so
every write of the run carries the worker's claim. A run that ends without completing or failing
the task is marked failed, so the dashboard never shows a search stuck in the queue. A write
refused because the claim was lost (a requeue or a reset, then another run's claim) ends the turn.

Crash safety: the task id and claim id are written to INFLIGHT before claude starts. A worker that
starts and finds INFLIGHT marks that task failed (if it is not finished) instead of running it
again, so a crash never runs a task twice. One worker per checkout: STATE_DIR/worker.lock.

The dashboard reads STATUS (see src/app/api/local-pipeline/route.ts).
"""
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
SKILL_ENV = ROOT / "skill" / "scripts" / ".env"
STATE_DIR = ROOT / ".convex"
STATUS = STATE_DIR / "hntd-worker.json"
INFLIGHT = STATE_DIR / "hntd-worker-inflight.json"
LOG_DIR = STATE_DIR / "pipeline-logs"
POLL_SECONDS = 5
GITHUB_RECHECK_SECONDS = 60

SETTINGS = ROOT / "scripts" / "local" / "pipeline-settings.json"
WRITABLE = ROOT / "skill" / "output"  # the one repo folder the pipeline's shell commands may write
# gh refuses to start when its config is unreadable, and the sandbox denies ~/.config/gh. A missing
# config folder is fine for gh, so claude's gh points at one and authenticates with GH_TOKEN.
GH_CONFIG_DIR = STATE_DIR / "gh-config-none"
# claude gets these from the worker's environment and nothing else (no cloud keys, no tokens of
# other tools). The pipeline reads its Convex URL and secret from skill/scripts/.env itself.
PASSED_ENV = {"PATH", "HOME", "USER", "LOGNAME", "SHELL", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE",
              "TERM", "GH_TOKEN", "GH_CONFIG_DIR", "GH_HOST", "XDG_CONFIG_HOME", "HTTPS_PROXY", "HTTP_PROXY",
              "NO_PROXY", "SSL_CERT_FILE"}
BASE_ENV = {k: v for k, v in os.environ.items()  # before dotenv touches os.environ
            if k in PASSED_ENV or (k.startswith(("CLAUDE_", "ANTHROPIC_")) and k != "CLAUDECODE")}
sys.path.insert(0, str(ROOT / "skill" / "scripts"))
import convex_client  # noqa: E402  (reads skill/scripts/.env: the local backend)
import github_token  # noqa: E402  (scripts/local, next to this file)

FINISHED = ("completed", "failed")


def log(msg: str) -> None:
    print(f"[worker {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def read_env_file(path: Path) -> dict:
    env = {}
    if path.exists():
        for line in path.read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() and not key.startswith("#"):
                env[key.strip()] = value.strip()
    return env


def write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    tmp.replace(path)


def pipeline_env() -> dict:
    """The environment claude and every gh call it makes run with.

    GH_TOKEN is the only way into GitHub from the sandbox: pipeline-settings.json denies reads of
    ~/.config/gh, so gh's own login is out of reach there. The token comes from skill/scripts/.env
    only, never from the user's gh login, which usually can write. No token: GitHub not connected."""
    env = dict(BASE_ENV, GH_CONFIG_DIR=str(GH_CONFIG_DIR))
    env.pop("GH_TOKEN", None)
    token = read_env_file(SKILL_ENV).get("GH_TOKEN")
    if token:
        env["GH_TOKEN"] = token
    return env


TOKEN_PROBLEMS = {  # github_token.Problem -> what the dashboard shows
    "rejected": "GitHub ha rifiutato il token.",
    "unreachable": "GitHub non risponde",
}
TOKEN_WARNING = ("Attenzione: la pipeline legge testo non affidabile e potrebbe usare questo token per modificare "
                 "dati su GitHub; la scelta sicura e' un token classico senza nessuna casella spuntata.")


class GithubCheck:
    """Can the pipeline reach GitHub with the saved token (github_token.py)? Cached, rechecked
    when the env file changes."""

    def __init__(self):
        self.result, self.checked_at, self.env_mtime = None, 0.0, None

    def get(self) -> dict:
        mtime = SKILL_ENV.stat().st_mtime if SKILL_ENV.exists() else None
        max_age = GITHUB_RECHECK_SECONDS if self.result and self.result["ok"] else POLL_SECONDS * 2
        if mtime != self.env_mtime or time.time() - self.checked_at >= max_age:
            self.result, self.checked_at, self.env_mtime = self._check(), time.time(), mtime
        return self.result

    @staticmethod
    def _check() -> dict:
        if not shutil.which("gh"):
            return {"ok": False, "error": "GitHub CLI (gh) non installato"}
        token = pipeline_env().get("GH_TOKEN")
        if not token:
            return {"ok": False, "error": "nessun token GitHub salvato"}
        verdict = github_token.check(token)
        if not verdict.login:
            return {"ok": False, "error": TOKEN_PROBLEMS[verdict.problem]}
        if verdict.read_only:
            return {"ok": True, "login": verdict.login}
        log(f"{TOKEN_WARNING} (scope: {verdict.scopes or 'non leggibili, token fine-grained'})")
        return {"ok": True, "login": verdict.login, "warning": TOKEN_WARNING}


def model_args() -> list:
    model = os.environ.get("HNTD_PIPELINE_MODEL", "").strip()
    return ["--model", model] if model else []


def final_result(log_text: str) -> dict:
    """The last `result` message of a stream-json log, or {}. The CLI does not put `type` first."""
    final = {}
    for line in log_text.splitlines():
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(msg, dict) and msg.get("type") == "result":
            final = msg
    return final


def other_than(char: str) -> str:
    """A glob set of every printable ASCII character except `char` and `/`. Sandbox globs have no
    negated set, only ranges."""
    sets, start = [], 0x20
    for cut in sorted({ord("/"), ord(char)}) + [0x7F]:
        if start < cut:
            sets.append(chr(start) if start == cut - 1 else f"{chr(start)}-{chr(cut - 1)}")
        start = cut + 1
    return f"[{''.join(sets)}]"


def everything_but(keep: Path) -> list:
    """denyWrite globs covering every path in the repo except `keep` and what is under it.

    allowWrite cannot reopen a folder inside a denied one (a write deny always wins), so the deny
    names the rest instead: at each level, every name but the one on the way to `keep`, new names
    included (a command cannot create ROOT/.npmrc). Not covered: a name that starts with a control
    or non-ASCII character."""
    globs, parent = [], ROOT
    for name in keep.relative_to(ROOT).parts:
        for i, char in enumerate(name):
            globs.append(f"{parent}/{name[:i]}{other_than(char)}*")
            if i:
                globs.append(f"{parent}/{name[:i]}")
        globs.append(f"{parent}/{name}?*")
        parent = parent / name
    return globs


def pipeline_settings() -> str:
    """pipeline-settings.json as a JSON string, completed for this checkout.

    - `./` sandbox paths become absolute: Claude Code resolves a relative sandbox path against the
      settings file's folder, not cwd.
    - sandbox.filesystem.denyRead is the one list of denied reads. Each entry also becomes a
      Read(...) deny rule for the file tools (Read, Grep, Glob), except a folder that holds the repo
      (~/Desktop here): a deny rule has no exception, so it would lock the pipeline out of the repo.
      For such a folder the sandbox re-allows the repo with allowRead, and the file tools can still
      read the rest of it.
    - the repo's write denials (everything_but)."""
    settings = json.loads(SETTINGS.read_text())
    fs = settings["sandbox"]["filesystem"]
    for key, paths in fs.items():
        fs[key] = [os.path.normpath(ROOT / p) if p.startswith("./") else p for p in paths]
    rules = settings["permissions"]["deny"]
    for path in fs["denyRead"]:
        if ROOT.is_relative_to(Path(path).expanduser()):
            fs["allowRead"] = [str(ROOT)]
            continue
        rule_path = path if path.startswith("~/") else "/" + path  # `//` = absolute in a rule
        rules += [f"Read({rule_path})", f"Read({rule_path}/**)"]
    fs["denyWrite"] = fs.get("denyWrite", []) + everything_but(WRITABLE)
    return json.dumps(settings)


def claude_command(prompt: str) -> list:
    # dontAsk: a tool call runs only if the settings allow it. Bash runs in Claude Code's sandbox:
    # network to GitHub and localhost only, writes only under skill/output, credential paths
    # unreadable (evidence: artifacts/local-mode/evidence/permissions/). The user's own Claude Code
    # config stays out: `--setting-sources project` drops their settings, hooks and plugins (a
    # personal PreToolUse hook that times out is a refusal under dontAsk, and their WebFetch(domain:)
    # allow rules would widen the sandbox's network allowlist), `--strict-mcp-config` their MCP
    # servers and claude.ai connectors. The project skill /github-hr and the login still work.
    return ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
            "--permission-mode", "dontAsk", "--setting-sources", "project", "--strict-mcp-config",
            "--settings", pipeline_settings(), *model_args()]


TOKEN_MARKER = "[GH_TOKEN]"


def new_log(task_id: str) -> Path:
    """An empty run log only this user can read: it records every tool output, so a command that
    prints the token puts it there until redact_token runs."""
    LOG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    LOG_DIR.chmod(0o700)  # mkdir's mode goes through the umask, and the folder may predate it
    path = LOG_DIR / f"{task_id}.jsonl"
    os.close(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600))
    path.chmod(0o600)
    return path


def redact_token(log_path: Path, token: str | None) -> str:
    """Replace every copy of `token` in the log with TOKEN_MARKER. Returns the log text."""
    text = log_path.read_text(errors="replace")
    if token and token in text:
        text = text.replace(token, TOKEN_MARKER)
        log_path.write_text(text)
    return text


def run_claude(task_id: str, claim_id: str, log_path: Path) -> dict:
    """Run the pipeline for one task. Returns the CLI's final `result` message (or {})."""
    cmd = claude_command(f"/github-hr run --task {task_id}")
    # The run's writes, its own `convex_client.py claim` included, carry the worker's claim.
    env = dict(pipeline_env(), **{convex_client.CLAIM_ID_ENV: claim_id})
    with log_path.open("w") as out:
        proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=out,
                                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        write_json(INFLIGHT, {"taskId": task_id, "pid": proc.pid, "claimId": claim_id})
        proc.wait()
    return final_result(redact_token(log_path, env.get("GH_TOKEN")))


def fail_if_unfinished(task_id: str, claim_id: str, reason: str) -> None:
    """Mark the task failed unless it is finished. A deleted search (the backend answers 404)
    and a lost claim count as finished. Any other error propagates, so the caller keeps INFLIGHT
    and retries."""
    try:
        status = convex_client.get_task(task_id).get("status")
    except requests.HTTPError as exc:
        if exc.response is None or exc.response.status_code != 404:
            raise
        log(f"{task_id}: the search was deleted, nothing to mark failed")
        return
    if status not in FINISHED:
        try:
            convex_client.update_task_status(task_id, "failed", reason, claim_id=claim_id)
        except convex_client.ClaimLost as exc:
            log(f"{task_id}: not marked failed, another run or a requeue or reset took the search ({exc})")
            return
        log(f"{task_id}: {status} -> failed ({reason[:120]})")


def recover_inflight() -> None:
    """A run was cut short (worker crash, or an error before cleanup): wait for its claude if it
    is still alive, then mark the task failed if unfinished. The task is never run again."""
    if not INFLIGHT.exists():
        return
    data = json.loads(INFLIGHT.read_text())
    pid = data.get("pid")
    while pid:
        try:
            os.kill(pid, 0)
        except (ProcessLookupError, PermissionError):
            break
        time.sleep(POLL_SECONDS)
    log_path = LOG_DIR / f"{data['taskId']}.jsonl"
    if log_path.exists():
        redact_token(log_path, pipeline_env().get("GH_TOKEN"))
    if data.get("claimId"):
        fail_if_unfinished(data["taskId"], data["claimId"],
                           "Interrotta: il worker locale si e' fermato durante l'elaborazione. "
                           "Crea di nuovo la ricerca per riprovare.")
    else:  # an older worker wrote INFLIGHT without its claim: nothing it may write any more
        log(f"{data['taskId']}: left by a worker that recorded no claim id, so it cannot be marked failed")
    INFLIGHT.unlink()


def process(task_id: str, github: dict) -> bool:
    """Claim the task and run it. False when the claim was not granted and nothing ran."""
    claim_id = str(uuid.uuid4())
    write_json(INFLIGHT, {"taskId": task_id, "pid": None, "claimId": claim_id})
    try:
        claim = convex_client.claim_task(task_id, claim_id)
    except convex_client.TaskNotFound:
        log(f"{task_id}: not claimed, the search was deleted")
        INFLIGHT.unlink()
        return False
    if not claim.get("claimed"):
        log(f"{task_id}: not claimed, it is {claim.get('status')}: another run holds it")
        INFLIGHT.unlink()
        return False
    log_path = new_log(task_id)
    write_status("running", github, taskId=task_id, log=str(log_path.relative_to(ROOT)))
    log(f"{task_id}: running claude {' '.join(model_args()) or '(default model)'}, log {log_path}")
    started = time.time()
    final = run_claude(task_id, claim_id, log_path)
    log(f"{task_id}: claude exited after {time.time() - started:.0f}s, "
        f"cost_usd={final.get('total_cost_usd')}, is_error={final.get('is_error')}, "
        f"denied_tool_calls={len(final.get('permission_denials') or [])}")
    last = str(final.get("result") or "nessun messaggio finale").strip().replace("\n", " ")
    fail_if_unfinished(task_id, claim_id, f"La pipeline si e' fermata senza finire: {last[:400]} "
                                f"(log: {log_path.relative_to(ROOT)})")
    INFLIGHT.unlink()
    return True


def write_status(state: str, github: dict | None, **extra) -> None:
    write_json(STATUS, {"updatedAt": int(time.time() * 1000), "state": state,
                        "github": github, **extra})


def main() -> None:
    STATE_DIR.mkdir(exist_ok=True)
    lock = (STATE_DIR / "worker.lock").open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit("another HNTD worker is already running on this checkout")
    if not shutil.which("claude"):
        log("Claude Code (claude) is not installed: searches will wait in the queue.")
    log(f"polling {convex_client.CONVEX_URL} every {POLL_SECONDS}s, model: "
        f"{os.environ.get('HNTD_PIPELINE_MODEL') or 'Claude Code default'}")
    github_check = GithubCheck()
    while True:
        github = None
        try:
            recover_inflight()
            github = github_check.get()
            pending = sorted(convex_client.get_pending_tasks(), key=lambda t: t.get("_creationTime", 0))
            if not pending:
                write_status("idle", github)
            elif not github["ok"]:
                write_status("github_missing", github, pendingCount=len(pending))
            elif not shutil.which("claude"):
                write_status("error", github, error="Claude Code (claude) non installato")
            else:
                if process(pending[0]["_id"], github):
                    continue  # more may be waiting; after a refused claim, wait a poll instead
        except Exception as exc:  # the backend restarting, a network blip: report and keep polling
            log(f"error: {exc}")
            write_status("error", github, error=str(exc)[:300])
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
