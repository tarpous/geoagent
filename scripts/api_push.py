"""Upload not-yet-remote commits via the GitHub Git Data API (Zscaler-safe)."""

from __future__ import annotations

import base64
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = "tarpous/geoagent"
API = "https://api.github.com"
ROOT = Path(__file__).resolve().parents[1]


def run(args: list[str]) -> str:
    return subprocess.check_output(args, text=True, cwd=ROOT).strip()


def token() -> str:
    return run(["gh", "auth", "token"])


def api(method: str, path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "geoagent-api-push",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} -> {exc.code}: {detail}") from exc


def commits_to_upload() -> list[str]:
    """Prefer commits ahead of origin/main; fall back to full history."""
    try:
        ahead = run(["git", "rev-list", "--reverse", "origin/main..HEAD"])
        if ahead:
            return ahead.splitlines()
    except subprocess.CalledProcessError:
        pass
    return run(["git", "rev-list", "--reverse", "HEAD"]).splitlines()


def main() -> int:
    commits = commits_to_upload()
    if not commits:
        print("nothing to upload")
        return 0

    ref = api("GET", f"/repos/{REPO}/git/ref/heads/main")
    parent = ref["object"]["sha"]
    print(f"base parent={parent}")
    print(f"uploading {len(commits)} commits")

    for sha in commits:
        subject = run(["git", "log", "-1", "--format=%s", sha])
        body = run(["git", "log", "-1", "--format=%b", sha])
        message = subject if not body else f"{subject}\n\n{body}"
        paths = run(["git", "ls-tree", "-r", "--name-only", sha]).splitlines()
        tree_items: list[dict] = []
        for path in paths:
            mode = run(["git", "ls-tree", sha, "--", path]).split()[0]
            content = subprocess.check_output(["git", "show", f"{sha}:{path}"], cwd=ROOT)
            try:
                text = content.decode("utf-8")
                tree_items.append(
                    {"path": path, "mode": mode, "type": "blob", "content": text}
                )
            except UnicodeDecodeError:
                blob = api(
                    "POST",
                    f"/repos/{REPO}/git/blobs",
                    {
                        "content": base64.b64encode(content).decode("ascii"),
                        "encoding": "base64",
                    },
                )
                tree_items.append(
                    {"path": path, "mode": mode, "type": "blob", "sha": blob["sha"]}
                )

        tree = api("POST", f"/repos/{REPO}/git/trees", {"tree": tree_items})
        commit = api(
            "POST",
            f"/repos/{REPO}/git/commits",
            {
                "message": message,
                "tree": tree["sha"],
                "parents": [parent],
            },
        )
        parent = commit["sha"]
        print(f"uploaded {sha[:8]} -> {parent[:8]} ({subject})")

    api("PATCH", f"/repos/{REPO}/git/refs/heads/main", {"sha": parent, "force": True})
    print(f"updated main -> {parent}")
    print(f"https://github.com/{REPO}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
