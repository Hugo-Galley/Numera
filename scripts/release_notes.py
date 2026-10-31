#!/usr/bin/env python3
"""Notes de version et bump SemVer calculés depuis les commits Conventional Commits.

    python3 scripts/release_notes.py --bump                  # patch | minor | major | none
    python3 scripts/release_notes.py --next                  # prochaine version proposée (ex. 0.3.0)
    python3 scripts/release_notes.py --notes v0.3.0          # notes Markdown (HEAD si le tag n'existe pas)

Les commits pris en compte vont du dernier tag `vX.Y.Z` (exclu) à HEAD, ou au tag demandé.
Sans tag existant, tout l'historique est lu et la base est `0.0.0`.
"""
import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

SUBJECT = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]+)\))?(?P<bang>!)?:\s*(?P<desc>.+)$")
TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")

# Sections des notes, dans l'ordre d'affichage ; les autres types (docs, test, chore, ...) restent muets.
SECTIONS = {
    "feat": "Nouveautés",
    "fix": "Corrections",
    "perf": "Performances",
    "refactor": "Refontes internes",
}
SEPARATOR = "\x1e"
FIELD = "\x1f"


@dataclass(frozen=True)
class Commit:
    sha: str
    type: str
    scope: str | None
    description: str
    breaking: bool


def parse_commit(sha: str, subject: str, body: str = "") -> Commit:
    match = SUBJECT.match(subject.strip())
    breaking_body = "BREAKING CHANGE" in body or "BREAKING-CHANGE" in body
    if not match:
        return Commit(sha, "other", None, subject.strip(), breaking_body)
    return Commit(
        sha,
        match["type"],
        match["scope"],
        match["desc"].strip(),
        bool(match["bang"]) or breaking_body,
    )


def suggest_bump(commits: list[Commit]) -> str | None:
    """major (rupture) > minor (feat) > patch (fix, perf) ; None si rien de visible pour l'utilisateur."""
    if any(c.breaking for c in commits):
        return "major"
    if any(c.type == "feat" for c in commits):
        return "minor"
    if any(c.type in ("fix", "perf") for c in commits):
        return "patch"
    return None


def bump_version(version: str, bump: str) -> str:
    major, minor, patch = (int(part) for part in version.split("."))
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def _line(commit: Commit) -> str:
    prefix = f"**{commit.scope}** : " if commit.scope else ""
    return f"- {prefix}{commit.description} (`{commit.sha[:7]}`)"


def render_notes(version: str, commits: list[Commit]) -> str:
    lines = [f"# Numera {version}", ""]
    breaking = [c for c in commits if c.breaking]
    if breaking:
        lines += ["## Changements incompatibles", *map(_line, breaking), ""]
    for kind, title in SECTIONS.items():
        entries = [c for c in commits if c.type == kind and not c.breaking]
        if entries:
            lines += [f"## {title}", *map(_line, entries), ""]
    if len(lines) == 2:
        lines += ["Maintenance et documentation uniquement.", ""]
    return "\n".join(lines)


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    return result.stdout


def last_tag(before: str = "HEAD") -> str | None:
    tags = [t for t in _git("tag", "--merged", before).split() if TAG.match(t)]
    return max(tags, key=lambda t: tuple(int(n) for n in TAG.match(t).groups()), default=None)


def commits_between(start: str | None, end: str = "HEAD") -> list[Commit]:
    rev = f"{start}..{end}" if start else end
    raw = _git("log", "--no-merges", f"--format=%H{FIELD}%s{FIELD}%b{SEPARATOR}", rev)
    commits = []
    for entry in raw.split(SEPARATOR):
        if entry.strip():
            sha, subject, body = entry.strip("\n").split(FIELD, 2)
            commits.append(parse_commit(sha, subject, body))
    return commits


def _tag_exists(tag: str) -> bool:
    return subprocess.run(["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"], cwd=REPO_ROOT).returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--bump", action="store_true")
    group.add_argument("--next", action="store_true")
    group.add_argument("--notes", metavar="TAG")
    args = parser.parse_args()

    if args.notes:
        end = args.notes if _tag_exists(args.notes) else "HEAD"
        start = last_tag(f"{end}^") if end != "HEAD" else last_tag()
        print(render_notes(args.notes.removeprefix("v"), commits_between(start, end)))
        return 0

    base = last_tag()
    bump = suggest_bump(commits_between(base))
    if args.bump:
        print(bump or "none")
    else:
        print(bump_version(base.removeprefix("v") if base else "0.0.0", bump) if bump else "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
