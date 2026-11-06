#!/usr/bin/env python3
"""Notes de version et bump SemVer calculés depuis les commits Conventional Commits.

    python3 scripts/release/release_notes.py --bump                  # patch | minor | major | none
    python3 scripts/release/release_notes.py --next                  # prochaine version proposée (ex. 0.3.0)
    python3 scripts/release/release_notes.py --notes v0.3.0          # notes Markdown (HEAD si le tag n'existe pas)

Les commits pris en compte vont du dernier tag `vX.Y.Z` (exclu) à HEAD, ou au tag demandé.
Sans tag existant, tout l'historique est lu et la base est `0.0.0`.
"""
import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SUBJECT = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]+)\))?(?P<bang>!)?:\s*(?P<desc>.+)$")
TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
PR_SUFFIX = re.compile(r"\s*\(#(\d+)\)$")
TRAILER = re.compile(r"^(co-authored-by|signed-off-by|reviewed-by|🤖)\b", re.IGNORECASE)

# Sections des notes, dans l'ordre d'affichage ; les autres types (docs, test, chore, ...) restent muets.
# Les `feat` en tête de liste (À la une) ne sont pas répétés dans « Nouveautés ».
SECTIONS = {
    "feat": "🆕 Nouveautés",
    "fix": "🐛 Corrections",
    "perf": "⚡ Performances",
}
# Portées d'outillage : ni « À la une », ni « Nouveautés » : elles vont sous « Sous le capot » avec les refontes.
INTERNAL_SCOPES = {"qualité", "ci", "release", "build", "tests", "test", "docs", "deps", "outillage"}
INTERNAL_TITLE = "🔧 Sous le capot"
HIGHLIGHTS_TITLE = "✨ À la une"
HIGHLIGHTS_MAX = 3
SUMMARY_MAX = 280
SCOPE_LABELS = {"front": "Frontend", "api": "API", "ui": "Interface", "mcp": "MCP", "nginx": "Nginx"}
SEPARATOR = "\x1e"
FIELD = "\x1f"


@dataclass(frozen=True)
class Commit:
    sha: str
    type: str
    scope: str | None
    description: str
    breaking: bool
    body: str = ""
    pr: int | None = None


def _split_pr(description: str) -> tuple[str, int | None]:
    """`(#48)` ajouté par le squash GitHub en fin de titre : devient un lien, pas du texte."""
    match = PR_SUFFIX.search(description)
    return (description[: match.start()].rstrip(), int(match[1])) if match else (description, None)


def parse_commit(sha: str, subject: str, body: str = "") -> Commit:
    match = SUBJECT.match(subject.strip())
    breaking_body = "BREAKING CHANGE" in body or "BREAKING-CHANGE" in body
    if not match:
        description, pr = _split_pr(subject.strip())
        return Commit(sha, "other", None, description, breaking_body, body, pr)
    description, pr = _split_pr(match["desc"].strip())
    return Commit(
        sha, match["type"], match["scope"], description, bool(match["bang"]) or breaking_body, body, pr
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


def scope_label(scope: str | None) -> str | None:
    if not scope:
        return None
    label = SCOPE_LABELS.get(scope.lower(), scope[:1].upper() + scope[1:])
    return label.replace(",", ", ")


def _capitalize(text: str) -> str:
    return text[:1].upper() + text[1:]


def is_internal(commit: Commit) -> bool:
    return commit.type == "refactor" or (commit.scope or "").lower() in INTERNAL_SCOPES


def summary(commit: Commit) -> str:
    """Premier paragraphe du corps du commit (le « pourquoi »), sans signatures, borné à SUMMARY_MAX."""
    paragraph: list[str] = []
    for raw in commit.body.splitlines():
        line = raw.strip()
        if TRAILER.match(line):
            break
        if not line:
            if paragraph:
                break
            continue
        if line.startswith(("-", "*")) and not paragraph:
            return ""
        paragraph.append(line)
    text = " ".join(paragraph)
    if len(text) <= SUMMARY_MAX:
        return text
    cut = text[:SUMMARY_MAX].rsplit(" ", 1)[0].rstrip(",;:")
    return f"{cut}…"


def _ref_text(commit: Commit, repo: str | None) -> str:
    if commit.pr:
        return f"[#{commit.pr}](https://github.com/{repo}/pull/{commit.pr})" if repo else f"#{commit.pr}"
    return f"`{commit.sha[:7]}`"


def _ref(commit: Commit, repo: str | None) -> str:
    return f" ({_ref_text(commit, repo)})"


def _line(commit: Commit, repo: str | None = None) -> str:
    label = scope_label(commit.scope)
    prefix = f"**{label}** · " if label else ""
    return f"- {prefix}{_capitalize(commit.description)}{_ref(commit, repo)}"


def _highlights(commits: list[Commit]) -> list[Commit]:
    """Les nouveautés (hors outillage) ; celles dont le corps explique le pourquoi passent en premier."""
    candidates = [c for c in commits if c.type == "feat" and not c.breaking and not is_internal(c)]
    candidates.sort(key=lambda c: not summary(c))  # tri stable : l'ordre git (récent d'abord) est conservé
    return candidates[:HIGHLIGHTS_MAX]


def _overview(commits: list[Commit]) -> str:
    def count(kind: str) -> int:
        return sum(1 for c in commits if c.type == kind and not is_internal(c))

    parts = [
        (count("feat"), "nouveauté", "nouveautés"),
        (count("fix"), "correction", "corrections"),
        (count("perf"), "amélioration de performance", "améliorations de performance"),
    ]
    text = " · ".join(f"{n} {one if n == 1 else many}" for n, one, many in parts if n)
    internal = sum(1 for c in commits if is_internal(c) and c.type in ("feat", "fix", "perf", "refactor"))
    if internal:
        text += f"{' · ' if text else ''}{internal} changement{'s' if internal > 1 else ''} interne{'s' if internal > 1 else ''}"
    return text


def render_notes(version: str, commits: list[Commit], repo: str | None = None, previous: str | None = None) -> str:
    lines = [f"# Numera {version}", ""]
    visible = [c for c in commits if c.type in ("feat", "fix", "perf", "refactor") or c.breaking]
    overview = _overview(commits)
    if overview:
        lines += [f"> {overview}", ""]

    breaking = [c for c in commits if c.breaking]
    if breaking:
        lines += ["## ⚠️ Changements incompatibles"]
        for c in breaking:
            lines += [_line(c, repo)]
            detail = summary(c)
            if detail:
                lines += [f"  {detail}"]
        lines += [""]

    highlights = _highlights([c for c in commits if not c.breaking])
    if highlights:
        lines += [f"## {HIGHLIGHTS_TITLE}", ""]
        for c in highlights:
            label = scope_label(c.scope)
            lines += [f"### {_capitalize(c.description)}", ""]
            if summary(c):
                lines += [summary(c), ""]
            lines += [f"<sub>{label + ' · ' if label else ''}{_ref_text(c, repo)}</sub>", ""]

    shown = {id(c) for c in highlights}
    for kind, title in SECTIONS.items():
        entries = [
            c for c in commits if c.type == kind and not c.breaking and not is_internal(c) and id(c) not in shown
        ]
        if entries:
            lines += [f"## {title}", *(_line(c, repo) for c in entries), ""]

    internal = [c for c in commits if is_internal(c) and not c.breaking and c.type in ("feat", "fix", "perf", "refactor")]
    if internal:
        lines += [f"## {INTERNAL_TITLE}", *(_line(c, repo) for c in internal), ""]

    if not visible:
        lines += ["Maintenance et documentation uniquement.", ""]

    lines += [
        "## Mettre à jour",
        "",
        "Télécharger le `docker-compose.yml` joint à cette release (il pointe sur les images de cette version), puis :",
        "",
        "```bash",
        "docker compose pull && docker compose up -d",
        "```",
        "",
    ]
    if repo and previous:
        lines += [
            f"**Changelog complet** : [{previous}…v{version}](https://github.com/{repo}/compare/{previous}...v{version})",
            "",
        ]
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


def github_repo() -> str | None:
    """`owner/name` depuis GITHUB_REPOSITORY (CI) ou le remote origin ; None hors GitHub."""
    env = os.environ.get("GITHUB_REPOSITORY")
    if env:
        return env
    try:
        url = _git("remote", "get-url", "origin").strip()
    except subprocess.CalledProcessError:
        return None
    match = re.search(r"github\.com[:/](?P<repo>[^/]+/[^/]+?)(?:\.git)?$", url)
    return match["repo"] if match else None


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
        print(render_notes(args.notes.removeprefix("v"), commits_between(start, end), github_repo(), start))
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
