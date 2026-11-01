"""Repository-Einstellungen nach dem GitHub-Blueprint ([repository] und [sponsoring] in .github/blueprint.toml).

Wird von apply.py aufgerufen. Einstellungen ändern braucht Admin-Rechte: lokal mit «gh auth login» als Eigentümer:in
bzw. über Claude. Der GITHUB_TOKEN in Actions darf das nicht – dort werden die Einstellungen nur geprüft und gemeldet.
Was GitHub nicht per API anbietet, erscheint als Liste «Von Hand» mit Link.
"""
from __future__ import annotations

import json
import subprocess

# Pull-Request-Profile: solo = eine Person bzw. kleines Team mit direkten Pushes, team = Beiträge über Pull Requests
PR_PROFILES = {
    "solo": {
        "allow_merge_commit": False, "allow_squash_merge": True, "allow_rebase_merge": True,
        "allow_auto_merge": False, "delete_branch_on_merge": True, "allow_update_branch": True,
        "squash_merge_commit_title": "PR_TITLE", "squash_merge_commit_message": "PR_BODY",
    },
    "team": {
        "allow_merge_commit": False, "allow_squash_merge": True, "allow_rebase_merge": False,
        "allow_auto_merge": True, "delete_branch_on_merge": True, "allow_update_branch": True,
        "squash_merge_commit_title": "PR_TITLE", "squash_merge_commit_message": "PR_BODY",
    },
}
FUNDING_KEYS = ["github", "buy_me_a_coffee", "ko_fi", "liberapay", "patreon", "open_collective", "polar"]


def _gh(*args: str, input_json: dict | None = None):
    cmd = ["gh", "api", *args]
    if input_json is not None:
        cmd += ["--input", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True, input=json.dumps(input_json) if input_json is not None else None)
    if r.returncode != 0:
        raise RuntimeError(f"gh api {args[-1] if args else ''}: {(r.stderr or r.stdout).strip()[:300]}")
    return json.loads(r.stdout) if r.stdout.strip() else None


def _auto(value, public: bool, if_public, if_private):
    return (if_public if public else if_private) if value == "auto" else value


def target(cfg: dict, current: dict, change_visibility: bool) -> tuple[dict, bool, list[str]]:
    """Gewünschte Einstellungen (PATCH /repos) und ob das Ziel öffentlich ist."""
    r = cfg.get("repository", {})
    notes: list[str] = []
    wants_public = r.get("sichtbarkeit", "privat") == "oeffentlich"
    is_public = current.get("visibility") == "public"
    public = wants_public if change_visibility else is_public
    if wants_public != is_public and not change_visibility:
        notes.append(f"Sichtbarkeit: konfiguriert «{r.get('sichtbarkeit')}», auf GitHub «{current.get('visibility')}» – "
                     "nicht geändert (nur mit --sichtbarkeit; vorher Checkliste «Öffentlich machen» prüfen)")
    profile = _auto(r.get("pr_profil", "auto"), public, "team", "solo")
    patch: dict = {
        "has_issues": bool(r.get("issues", True)),
        "has_projects": bool(r.get("projekte", True)),
        "has_wiki": bool(_auto(r.get("wiki", "auto"), public, True, False)),
        "has_discussions": bool(_auto(r.get("diskussionen", "auto"), public, True, False)),
        "web_commit_signoff_required": bool(_auto(r.get("web_commit_signoff", "auto"), public, True, False)),
        **PR_PROFILES[profile],
    }
    if not public and patch["has_wiki"]:
        notes.append("Wiki in privaten Repositorys nur mit kostenpflichtigem Plan – ausgeschaltet")
        patch["has_wiki"] = False
    if r.get("standard_branch"):
        patch["default_branch"] = r["standard_branch"]
    if "vorlage" in r:
        patch["is_template"] = bool(r["vorlage"])
    if r.get("beschreibung"):
        patch["description"] = r["beschreibung"]
    if r.get("webseite"):
        patch["homepage"] = r["webseite"]
    if change_visibility and wants_public != is_public:
        patch["visibility"] = "public" if wants_public else "private"
    if public and _auto(r.get("secret_scanning", "auto"), public, True, False):
        patch["security_and_analysis"] = {
            "secret_scanning": {"status": "enabled"},
            "secret_scanning_push_protection": {"status": "enabled"},
        }
    return patch, public, notes


def rulesets(cfg: dict, public: bool) -> list[dict]:
    r = cfg.get("repository", {})
    if not r.get("branch_schutz", True):
        return []
    bypass = [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}]  # Admin (Eigentümer:in)
    rules = [{"type": "deletion"}, {"type": "non_fast_forward"}]
    checks = list(r.get("pflicht_pruefungen", []))
    if checks:
        rules.append({"type": "required_status_checks", "parameters": {
            "strict_required_status_checks_policy": False, "do_not_enforce_on_create": True,
            "required_status_checks": [{"context": c} for c in checks]}})
    if _auto(r.get("lineare_historie", "auto"), public, True, False):
        rules.append({"type": "required_linear_history"})
    if _auto(cfg.get("copilot", {}).get("code_review", False), public, True, False):
        rules.append({"type": "copilot_code_review", "parameters": {"review_on_push": True, "review_draft_pull_requests": False}})
    if _auto(r.get("pr_pflicht", "auto"), public, True, False):
        rules.append({"type": "pull_request", "parameters": {
            "required_approving_review_count": 0, "dismiss_stale_reviews_on_push": False,
            "require_code_owner_review": False, "require_last_push_approval": False,
            "required_review_thread_resolution": False}})
    return [
        {"name": "Standard-Branch schützen", "target": "branch", "enforcement": "active", "bypass_actors": bypass,
         "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}}, "rules": rules},
        {"name": "Versions-Tags schützen", "target": "tag", "enforcement": "active", "bypass_actors": bypass,
         "conditions": {"ref_name": {"include": ["refs/tags/v*"], "exclude": []}},
         "rules": [{"type": "deletion"}, {"type": "update"}, {"type": "non_fast_forward"}]},
    ]


def funding(cfg: dict) -> str:
    """Inhalt für .github/FUNDING.yml (leer = keine Unterstützungsmöglichkeiten konfiguriert)."""
    s = cfg.get("sponsoring", {})
    lines = []
    for key in FUNDING_KEYS:
        value = s.get(key, "")
        if value:
            lines.append(f"{key}: {json.dumps(value) if isinstance(value, list) else value}")
    links = [l for l in s.get("links", []) if l][:4]
    if links:
        lines.append("custom: [" + ", ".join(json.dumps(l) for l in links) + "]")
    return ("# Unterstützungsmöglichkeiten (GitHub-Blueprint, [sponsoring] in .github/blueprint.toml)\n" + "\n".join(lines) + "\n") if lines else ""


def manual_steps(cfg: dict, repo: str, public: bool) -> list[str]:
    base = f"https://github.com/{repo}/settings"
    steps = [
        f"Social Preview: Bild 1280×640 hochladen (.github/social-preview.png, erzeugt mit "
        f"«python3 .github/blueprint/social_preview.py --repo {repo}») – {base} → Social preview",
        f"Releases: «Enable release immutability» an (Tags und Dateien veröffentlichter Releases unveränderlich) – {base} → Releases",
        f"Startseite: Releases, Packages, Deployments in der Seitenleiste ein-/ausblenden – https://github.com/{repo} → Zahnrad bei «About»",
        f"Pushes: «Limit how many branches and tags can be updated in a single push» (Empfehlung {'an, 5' if public else 'aus'}) – {base} → Pushes",
        f"Issues: «Auto-close issues with merged linked pull requests» an – {base} → Issues",
        f"Branches: keine klassischen Branch-Schutzregeln anlegen – der Schutz kommt aus den Rulesets ({base}/rules)",
        f"Planung: GitHub-Projekt (Board) mit Feld «Status» = Triage, Bereit, In Arbeit, Beta-Test, Erledigt und Ansichten Board / Tabelle nach Meilenstein / Roadmap anlegen und mit dem Repository verknüpfen (gh project create --owner {repo.split('/')[0]} --title …) – docs/GITHUB-ABLAUF.md",
        f"Codespaces: Prebuilds nur bei Bedarf; Konfiguration .devcontainer/devcontainer.json – {base}/codespaces",
    ]
    cp = cfg.get("copilot", {})
    if cp.get("aktiv", False):
        steps += [
            f"Copilot: Code Review automatisch für Pull Requests (Ruleset-Regel gesetzt, Lizenz nötig); Coding Agent einschalten, "
            f"Firewall «Recommended allowlist» an, MCP-Server nur bei Bedarf, Umgebung «copilot» für Agent-Secrets – {base}/copilot",
        ]
    if public:
        steps += [
            f"Sponsorships: «Sponsorships» einschalten (zeigt den Sponsor-Knopf aus .github/FUNDING.yml) – {base} → Features",
            f"Preserve this repository (GitHub Archive Program): einschalten – {base} → Archives",
            f"Issue-Rechte: bei Spam vorübergehend «Interaction limits» (nur bisherige Nutzer:innen bzw. Mitwirkende) – {base}/interaction_limits",
            f"Code review limits: «Limit to users explicitly granted read or higher access» an (nur Mitwirkende können freigeben/Änderungen verlangen) – {base}/code_review_limits",
        ]
    return steps


def apply_settings(cfg: dict, repo: str, rep, change_visibility: bool, root=None) -> list[str]:
    current = _gh(f"repos/{repo}")
    admin = bool((current.get("permissions") or {}).get("admin"))
    patch, public, notes = target(cfg, current, change_visibility)
    for n in notes:
        rep.warn(n)
    diff = {}
    for k, v in patch.items():
        if k == "security_and_analysis":
            cur = current.get("security_and_analysis") or {}
            if any((cur.get(x) or {}).get("status") != y["status"] for x, y in v.items()):
                diff[k] = v
        elif current.get(k) != v:
            diff[k] = v
    if diff:
        text = ", ".join(f"{k}={'…' if isinstance(v, dict) else v}" for k, v in diff.items())
        if not admin:
            rep.warn(f"Einstellungen weichen ab ({text}) – ohne Admin-Rechte nicht geändert; lokal mit «gh auth login» als "
                     "Eigentümer:in bzw. über Claude anwenden")
        else:
            rep.do(f"Einstellungen: {text}")
            if not rep.dry:
                _gh("-X", "PATCH", f"repos/{repo}", input_json=diff)
    if admin:
        try:
            existing = {x["name"] for x in _gh(f"repos/{repo}/rulesets")}
            for rs in rulesets(cfg, public):
                if rs["name"] in existing:
                    continue
                rep.do(f"Ruleset «{rs['name']}» angelegt")
                if not rep.dry:
                    _gh("-X", "POST", f"repos/{repo}/rulesets", input_json=rs)
        except RuntimeError as e:
            rep.warn(f"Rulesets nicht möglich ({e}) – bei privaten Repositorys im Free-Plan nicht verfügbar")
    topics = cfg.get("repository", {}).get("themen", [])
    if topics and admin and sorted(current.get("topics") or []) != sorted(topics):
        rep.do(f"Themen: {', '.join(topics)}")
        if not rep.dry:
            _gh("-X", "PUT", f"repos/{repo}/topics", input_json={"names": topics})
    todo: list[str] = []
    if admin:
        import advanced
        from pathlib import Path
        todo = advanced.apply_advanced(cfg, repo, rep, public, current, Path(root) if root else Path.cwd())
    return todo + manual_steps(cfg, repo, public)
