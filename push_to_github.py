"""Create a new GitHub repo and push this project to it.

The token is read from the PAT file at
``~/Library/PPM/PAT/Tokens_29_06_2026_14_42_39.pat`` (or whichever path the
``--token-file`` arg points to). The file is expected to contain a GitHub PAT
either as the entire contents, or on a line beginning with ``ghp_`` /
``github_pat_``.

Run:
    python push_to_github.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen


DEFAULT_TOKEN_FILE = Path.home() / "Library" / "PPM" / "PAT" / "Tokens_29_06_2026_14_42_39.pat"
DEFAULT_OWNER = "tsuhasqni-pixel"
DEFAULT_REPO = "internal-accounting"
DEFAULT_VISIBILITY = "public"


def _extract_token(text: str) -> str | None:
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        m = re.search(r"(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})", s)
        if m:
            return m.group(1)
    s = text.strip()
    if re.fullmatch(r"[A-Za-z0-9_\-]{20,}", s):
        return s
    return None


def read_token(token_file: Path) -> str:
    if not token_file.exists():
        raise SystemExit(f"[ERROR] token file not found: {token_file}")
    text = token_file.read_text(encoding="utf-8", errors="ignore")
    token = _extract_token(text)
    if not token:
        raise SystemExit(
            f"[ERROR] could not find a GitHub PAT in {token_file}. "
            "Expected ghp_… or github_pat_…"
        )
    return token


def api(method: str, path: str, token: str, payload: dict | None = None) -> dict:
    body = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "internal-accounting-pusher",
    }
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(f"https://api.github.com{path}", data=body, headers=headers, method=method)
    with urlopen(req) as resp:
        text = resp.read().decode("utf-8")
        if not text:
            return {}
        return json.loads(text)


def whoami(token: str) -> str:
    return api("GET", "/user", token).get("login", "")


def repo_exists(owner: str, repo: str, token: str) -> bool:
    try:
        api("GET", f"/repos/{owner}/{repo}", token)
        return True
    except Exception:
        return False


def create_repo(owner: str, repo: str, token: str, visibility: str) -> None:
    me = whoami(token)
    is_org = me.lower() != owner.lower()
    payload = {
        "name": repo,
        "description": "Internal management accounting tool (standard cost, variance analysis, CVP)",
        "private": visibility == "private",
        "auto_init": False,
    }
    path = f"/orgs/{owner}/repos" if is_org else "/user/repos"
    api("POST", path, token, payload)


def run(cmd: list[str], cwd: Path, env: dict | None = None) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(cwd), env=env, check=True)


def git_push(repo_dir: Path, owner: str, repo: str, token: str) -> None:
    env = os.environ.copy()
    remote_url = f"https://github.com/{owner}/{repo}.git"
    if not (repo_dir / ".git").exists():
        run(["git", "init", "-b", "main"], repo_dir)
    existing_remote = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=str(repo_dir), capture_output=True, text=True,
    ).stdout.strip()
    if not existing_remote:
        run(["git", "remote", "add", "origin", remote_url], repo_dir)
    elif existing_remote != remote_url:
        run(["git", "remote", "set-url", "origin", remote_url], repo_dir)

    run(["git", "add", "-A"], repo_dir)
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(repo_dir), capture_output=True, text=True,
    ).stdout.strip()
    if status or subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(repo_dir),
        capture_output=True, text=True,
    ).returncode != 0:
        run(["git", "commit", "-m", "Initial commit: internal management accounting tool"], repo_dir)

    auth_header = f"http.extraHeader=Authorization: Bearer {token}"
    run(["git", "-c", auth_header, "push", "-u", "origin", "main"], repo_dir, env=env)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_FILE)
    parser.add_argument("--owner", default=DEFAULT_OWNER)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--visibility", choices=["public", "private"], default=DEFAULT_VISIBILITY)
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    token = read_token(args.token_file)

    print(f"GitHub login: {whoami(token)}")
    print(f"Target      : {args.owner}/{args.repo} ({args.visibility})")
    print(f"Project dir : {here}")

    if not repo_exists(args.owner, args.repo, token):
        print("[+] creating remote repository ...")
        create_repo(args.owner, args.repo, token, args.visibility)
    else:
        print("[=] remote repository already exists")

    git_push(here, args.owner, args.repo, token)
    print(f"\n[OK] pushed to https://github.com/{args.owner}/{args.repo}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"\n[FAIL] command failed: {e}", file=sys.stderr)
        sys.exit(1)
