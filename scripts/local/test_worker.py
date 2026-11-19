"""Tests for the local pipeline worker: which GitHub token claude gets, and reading a run's result.

GitHub's answer to the token check is faked; no token reaches the network.

Run: skill/scripts/.venv/bin/python -m pytest scripts/local/test_worker.py
"""
import json
import os
import re
import sys
from pathlib import Path

import pytest
import requests

# convex_client exits at import without a backend; nothing here talks to it.
os.environ.setdefault("CONVEX_SITE_URL", "http://127.0.0.1:9")
os.environ.setdefault("API_SECRET", "test")
sys.path.insert(0, str(Path(__file__).parent))
import worker  # noqa: E402


@pytest.fixture
def fake_gh(tmp_path, monkeypatch):
    """A `gh` on the worker's PATH whose `auth token` prints LOGIN_TOKEN, or fails if it is empty.
    Every call is recorded in calls.txt: the worker must never call it for a token."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "calls.txt"
    gh = bin_dir / "gh"
    gh.write_text(f"""#!/bin/sh
echo "$*" >> "{calls}"
if [ "$1 $2" = "auth token" ] && [ -n "$LOGIN_TOKEN" ]; then echo "$LOGIN_TOKEN"; exit 0; fi
echo "not logged in" >&2; exit 1
""")
    gh.chmod(0o755)
    monkeypatch.setitem(worker.BASE_ENV, "PATH", f"{bin_dir}:/usr/bin:/bin")
    monkeypatch.setenv("PATH", f"{bin_dir}:/usr/bin:/bin")
    monkeypatch.delitem(worker.BASE_ENV, "GH_TOKEN", raising=False)
    monkeypatch.setattr(worker, "SKILL_ENV", tmp_path / ".env")

    def login(token: str):
        monkeypatch.setitem(worker.BASE_ENV, "LOGIN_TOKEN", token)

    login("")
    return login, calls


def test_token_in_env_file_is_the_pipelines_token(fake_gh, tmp_path):
    (tmp_path / ".env").write_text("CONVEX_SITE_URL=http://127.0.0.1:3211\nGH_TOKEN=file-token\n")
    assert worker.pipeline_env()["GH_TOKEN"] == "file-token"


def test_the_gh_login_token_is_never_used(fake_gh, tmp_path):
    login, calls = fake_gh
    login("login-token")
    (tmp_path / ".env").write_text("GH_TOKEN=\n")
    assert "GH_TOKEN" not in worker.pipeline_env()
    assert not worker.GithubCheck._check()["ok"]
    assert not calls.exists()


def test_without_any_token_claude_gets_none(fake_gh, monkeypatch):
    monkeypatch.setitem(worker.BASE_ENV, "GH_TOKEN", "inherited-from-the-shell")
    assert "GH_TOKEN" not in worker.pipeline_env()


@pytest.fixture
def github_user(monkeypatch):
    """GitHub's answer to GET /user, faked: set `scopes` to the X-OAuth-Scopes header (None: no
    header). Returns the list of tokens the check sent."""
    sent = []

    def answer(scopes):
        def fetch_user(token):
            sent.append(token)
            return 200, {} if scopes is None else {"x-oauth-scopes": scopes}, b'{"login": "octocat"}'
        monkeypatch.setattr(worker.github_token, "fetch_user", fetch_user)
    answer.sent = sent
    return answer


def test_github_check_without_a_token(fake_gh):
    assert worker.GithubCheck._check() == {"ok": False, "error": "nessun token GitHub salvato"}


def test_github_check_accepts_a_saved_token_with_no_scopes(fake_gh, github_user, tmp_path):
    github_user("")
    (tmp_path / ".env").write_text("GH_TOKEN=file-token\n")
    assert worker.GithubCheck._check() == {"ok": True, "login": "octocat"}
    assert github_user.sent == ["file-token"]


@pytest.mark.parametrize("scopes", ["repo, workflow", None])
def test_github_check_accepts_a_saved_token_that_could_write_with_a_warning(
        fake_gh, github_user, tmp_path, capsys, scopes):
    github_user(scopes)
    (tmp_path / ".env").write_text("GH_TOKEN=could-write\n")
    assert worker.GithubCheck._check() == {"ok": True, "login": "octocat", "warning": worker.TOKEN_WARNING}
    assert capsys.readouterr().out.count(worker.TOKEN_WARNING) == 1


def test_github_check_reports_a_token_github_rejects(fake_gh, tmp_path, monkeypatch):
    monkeypatch.setattr(worker.github_token, "fetch_user", lambda token: (401, {}, b""))
    (tmp_path / ".env").write_text("GH_TOKEN=revoked\n")
    assert worker.GithubCheck._check() == {"ok": False, "error": "GitHub ha rifiutato il token."}


def test_github_check_asks_github_once_per_saved_token(fake_gh, github_user, tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(worker.github_token, "fetch_user", lambda token: sent.append(token) or (401, {}, b""))
    env = tmp_path / ".env"
    env.write_text("GH_TOKEN=revoked\n")
    check = worker.GithubCheck()
    assert [check.get()["ok"] for _ in range(5)] == [False] * 5
    assert sent == ["revoked"]
    github_user("")
    env.write_text("GH_TOKEN=no-scopes\n")
    os.utime(env, (1, 1))  # a new mtime even when the rewrite lands in the same clock tick
    assert check.get() == {"ok": True, "login": "octocat"}
    assert github_user.sent == ["no-scopes"]


def test_claudes_gh_never_reads_the_users_gh_config(fake_gh, monkeypatch):
    monkeypatch.setitem(worker.BASE_ENV, "GH_CONFIG_DIR", "/elsewhere/gh")
    assert worker.pipeline_env()["GH_CONFIG_DIR"] == str(worker.GH_CONFIG_DIR)
    assert not worker.GH_CONFIG_DIR.exists()


def sandbox_regex(glob: str) -> re.Pattern:
    """How Claude Code 2.1.327 turns a sandbox glob without `**` into the macOS profile's regex
    (functions W, X and der in its bundle): a [set] keeps its members with .^$+{}()|\\ escaped, so
    it is never negated; the entry covers the path and everything under it."""
    def escape(text: str, specials: str) -> str:
        return "".join("\\" + c if c in specials else c for c in text)

    def convert(part: str) -> str:
        if part in ("*", "?"):
            return {"*": "[^/]*", "?": "[^/]"}[part]
        if part.startswith("["):
            return "[" + escape(part[1:-1], ".^$+{}()|\\") + "]"
        return escape(part, ".*+?^${}()|[]\\")

    body = "".join(convert(p) for p in re.split(r"(\[[^\]]*\]|\*|\?)", glob))
    return re.compile(f"^{body}(/.*)?$")


def writable(path: str) -> bool:
    denials = json.loads(worker.pipeline_settings())["sandbox"]["filesystem"]["denyWrite"]
    return not any(sandbox_regex(g).match(f"{worker.ROOT}/{path}") for g in denials)


@pytest.mark.parametrize("path", ["skill/output/result-x.json", "skill/output/sub/new.json"])
def test_the_pipeline_may_write_under_skill_output(path):
    assert writable(path)


@pytest.mark.parametrize("path", [
    "package.json", ".npmrc", ".env", "skill/scripts/convex_client.py", "skill/scripts/new.py",
    "skill/SKILL.md", "skill/new", "skill/out", "skill/outputs/x", "skills/x", "s", "skillx",
    "scripts/local/worker.py", ".convex/hntd-worker.json", "S"])
def test_the_pipeline_may_not_write_anywhere_else_in_the_repo(path):
    assert not writable(path)


def test_settings_paths_are_absolute_in_the_repo():
    fs = json.loads(worker.pipeline_settings())["sandbox"]["filesystem"]
    assert str(worker.ROOT / ".env.local") in fs["denyRead"]
    assert all(p.startswith(("/", "~/")) for p in fs["denyRead"] + fs["denyWrite"])


def test_denied_reads_are_one_list_for_the_sandbox_and_the_file_tools(monkeypatch):
    raw = json.loads(worker.SETTINGS.read_text())
    assert not any(r.startswith("Read(") for r in raw["permissions"]["deny"])  # generated, not written
    monkeypatch.setattr(worker, "ROOT", Path.home() / "Desktop" / "some folder" / "hntd")
    monkeypatch.setattr(worker, "WRITABLE", worker.ROOT / "skill" / "output")
    settings = json.loads(worker.pipeline_settings())
    fs, rules = settings["sandbox"]["filesystem"], settings["permissions"]["deny"]
    for path in ["~/.zsh_history", "~/Library/Keychains", "~/Documents"]:
        assert path in fs["denyRead"] and f"Read({path}/**)" in rules
    env_local = f"{worker.ROOT}/.env.local"
    assert env_local in fs["denyRead"] and f"Read(/{env_local})" in rules
    # ~/Desktop holds the repo: the sandbox denies it and re-allows the repo; a Read rule has no
    # exception, so there is none for it.
    assert "~/Desktop" in fs["denyRead"] and fs["allowRead"] == [str(worker.ROOT)]
    assert not any(r.startswith("Read(~/Desktop") for r in rules)


def test_a_repo_outside_the_denied_folders_needs_no_allow_read(monkeypatch):
    monkeypatch.setattr(worker, "ROOT", Path("/opt/hntd"))
    monkeypatch.setattr(worker, "WRITABLE", worker.ROOT / "skill" / "output")
    settings = json.loads(worker.pipeline_settings())
    assert "allowRead" not in settings["sandbox"]["filesystem"]
    assert "Read(~/Desktop/**)" in settings["permissions"]["deny"]


@pytest.fixture
def fake_claude(tmp_path, monkeypatch):
    """A `claude` that prints the GH_TOKEN it got, as a careless command in a run would."""
    bin_dir = tmp_path / "claude-bin"
    bin_dir.mkdir()
    claude = bin_dir / "claude"
    claude.write_text('#!/bin/sh\necho "{\\"type\\": \\"result\\", \\"result\\": \\"token $GH_TOKEN\\"}"\n')
    claude.chmod(0o755)
    monkeypatch.setitem(worker.BASE_ENV, "PATH", f"{bin_dir}:/usr/bin:/bin")
    monkeypatch.setattr(worker, "SKILL_ENV", tmp_path / ".env")
    (tmp_path / ".env").write_text("GH_TOKEN=saved-token-value-123\n")
    monkeypatch.setattr(worker, "LOG_DIR", tmp_path / "pipeline-logs")
    monkeypatch.setattr(worker, "INFLIGHT", tmp_path / "inflight.json")


def test_run_log_is_private_and_holds_no_token(fake_claude):
    log_path = worker.new_log("t1")
    final = worker.run_claude("t1", log_path)
    assert oct(worker.LOG_DIR.stat().st_mode & 0o777) == "0o700"
    assert oct(log_path.stat().st_mode & 0o777) == "0o600"
    assert "saved-token-value-123" not in log_path.read_text()
    assert final["result"] == f"token {worker.TOKEN_MARKER}"


def test_run_log_folder_made_by_an_older_worker_becomes_private(fake_claude):
    worker.LOG_DIR.mkdir(mode=0o755)
    worker.LOG_DIR.chmod(0o755)
    worker.new_log("t1")
    assert oct(worker.LOG_DIR.stat().st_mode & 0o777) == "0o700"


def http_error(status: int) -> requests.HTTPError:
    """The error convex_client raises for an HTTP error status from the backend."""
    response = requests.Response()
    response.status_code = status
    return requests.HTTPError(f"{status} from the backend", response=response)


@pytest.fixture
def backend(fake_claude, tmp_path, monkeypatch):
    """The worker's state files under tmp_path and a backend that holds no task: get_task raises
    `backend.error` (a 404, as for a deleted search). Status updates are recorded."""
    monkeypatch.setattr(worker, "ROOT", tmp_path)
    monkeypatch.setattr(worker, "WRITABLE", tmp_path / "skill" / "output")
    monkeypatch.setattr(worker, "STATUS", tmp_path / "status.json")

    class Backend:
        error = http_error(404)
        updates = []

        @staticmethod
        def get_task(task_id):
            raise Backend.error

    monkeypatch.setattr(worker.convex_client, "get_task", Backend.get_task)
    monkeypatch.setattr(worker.convex_client, "update_task_status",
                        lambda task_id, status, error=None: Backend.updates.append((task_id, status)))
    return Backend


def test_a_search_deleted_during_its_run_counts_as_finished(backend):
    worker.process("t1", {"ok": True})
    assert not worker.INFLIGHT.exists()
    assert backend.updates == [("t1", "processing")]


def test_a_crashed_run_of_a_deleted_search_is_cleared(backend):
    worker.write_json(worker.INFLIGHT, {"taskId": "t1", "pid": None})
    worker.recover_inflight()
    assert not worker.INFLIGHT.exists()
    assert backend.updates == []


@pytest.mark.parametrize("error", [http_error(500), requests.ConnectionError("backend restarting")])
def test_a_backend_that_does_not_answer_keeps_the_run_for_the_next_loop(backend, error):
    backend.error = error
    worker.write_json(worker.INFLIGHT, {"taskId": "t1", "pid": None})
    with pytest.raises(requests.RequestException):
        worker.recover_inflight()
    assert json.loads(worker.INFLIGHT.read_text()) == {"taskId": "t1", "pid": None}


def test_claude_runs_without_the_users_own_config():
    cmd = worker.claude_command("/github-hr run --task t1")
    assert cmd[cmd.index("--setting-sources") + 1] == "project"
    assert "--strict-mcp-config" in cmd
    assert cmd[cmd.index("--permission-mode") + 1] == "dontAsk"
    assert not {"--bare", "--safe-mode", "--disable-slash-commands"} & set(cmd)  # they drop the skill or the login


# Field order as Claude Code 2.1.327 writes it: `type` is not the first key.
RESULT = {"duration_api_ms": 208680, "total_cost_usd": 3.25, "permission_denials": [
    {"tool_name": "Bash", "tool_use_id": "t1", "tool_input": {"command": "f() { :; }"}}],
    "is_error": False, "num_turns": 31, "subtype": "success", "result": "done", "type": "result"}


def test_final_result_reads_a_result_line_whose_type_is_not_first():
    log = "\n".join([json.dumps({"type": "system", "subtype": "init"}), "not json {",
                     json.dumps({"type": "assistant", "message": {}}), json.dumps(RESULT)])
    final = worker.final_result(log)
    assert (final["total_cost_usd"], final["is_error"], len(final["permission_denials"])) == (3.25, False, 1)


def test_final_result_keeps_the_last_result_and_is_empty_without_one():
    first = dict(RESULT, result="first")
    assert worker.final_result(json.dumps(first) + "\n" + json.dumps(RESULT))["result"] == "done"
    assert worker.final_result('{"type":"system"}\n') == {}


# Issue #3: the worker works on a search only after its claim (pending -> processing) succeeds.

@pytest.fixture
def worker_run(tmp_path, monkeypatch):
    """process() with the backend faked and a `claude` that records the claim it was given.
    Returns the list of backend status writes and the file claude writes when it starts."""
    started = tmp_path / "claude-started"
    bin_dir = tmp_path / "claude-bin"
    bin_dir.mkdir()
    claude = bin_dir / "claude"
    claude.write_text(f'#!/bin/sh\necho "$HNTD_CLAIMED_TASK" > "{started}"\n'
                      'echo "{\\"type\\": \\"result\\", \\"result\\": \\"done\\"}"\n')
    claude.chmod(0o755)
    monkeypatch.setitem(worker.BASE_ENV, "PATH", f"{bin_dir}:/usr/bin:/bin")
    monkeypatch.setattr(worker, "SKILL_ENV", tmp_path / ".env")
    monkeypatch.setattr(worker, "LOG_DIR", tmp_path / "pipeline-logs")
    monkeypatch.setattr(worker, "INFLIGHT", tmp_path / "inflight.json")
    monkeypatch.setattr(worker, "STATUS", tmp_path / "status.json")
    monkeypatch.setattr(worker, "ROOT", tmp_path)
    monkeypatch.setattr(worker, "WRITABLE", tmp_path / "skill" / "output")
    writes = []
    monkeypatch.setattr(worker.convex_client, "update_task_status",
                        lambda task_id, status, error=None: writes.append((task_id, status)))
    monkeypatch.setattr(worker.convex_client, "get_task", lambda task_id: {"status": "completed"})
    return writes, started


@pytest.mark.parametrize("answer", [{"claimed": False, "status": "processing"}, "gone"])
def test_a_refused_claim_starts_no_run_and_marks_nothing(worker_run, monkeypatch, answer):
    writes, started = worker_run

    def claim_task(task_id):
        if answer == "gone":
            raise worker.convex_client.TaskNotFound(task_id)
        return answer

    monkeypatch.setattr(worker.convex_client, "claim_task", claim_task)
    worker.process("t1", {"ok": True})
    assert not started.exists()
    assert not worker.INFLIGHT.exists()
    assert writes == []


def test_a_granted_claim_runs_claude_holding_it(worker_run, monkeypatch):
    writes, started = worker_run
    claims = []
    monkeypatch.setattr(worker.convex_client, "claim_task",
                        lambda task_id: claims.append(task_id) or {"claimed": True})
    worker.process("t1", {"ok": True})
    assert claims == ["t1"]
    assert started.read_text().strip() == "t1"
    assert not worker.INFLIGHT.exists()
    assert writes == []
    assert "HNTD_CLAIMED_TASK" not in worker.pipeline_env()
