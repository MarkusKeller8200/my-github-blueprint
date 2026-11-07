"""Weitere Repository-Einstellungen des GitHub-Blueprints: Actions, OIDC, Umgebungen, Webhooks, Pages,
Advanced Security, Deploy-Keys, Secrets und Variablen. Wird von settings.apply_settings aufgerufen
(nur mit Admin-Rechten). Fehlende Rechte oder Funktionen, die der Plan nicht bietet, werden gemeldet, nicht erzwungen.

Geheime Werte stehen NIE in der Konfiguration: Secrets werden aus gleichnamigen Umgebungsvariablen gesetzt
(z. B. DEPLOY_SSH_KEY=… python3 apply.py), sonst – falls eingeschaltet – mit einem Platzhalter angelegt, damit der
Name sichtbar ist. Platzhalter müssen vor dem ersten Einsatz ersetzt werden.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from urllib.parse import quote

from settings import _auto, _gh

PLACEHOLDER = "NOCH-NICHT-GESETZT"


def _try(rep, label: str, fn) -> bool:
    try:
        fn()
        return True
    except RuntimeError as e:
        rep.warn(f"{label}: nicht möglich ({str(e)[:160]})")
        return False


# --- Actions ---------------------------------------------------------------------------------------------------

def actions(cfg: dict, repo: str, rep, public: bool) -> None:
    a = cfg.get("actions", {})
    allowed = a.get("erlaubte_actions", "ausgewaehlt")
    perm = {"enabled": True, "allowed_actions": {"alle": "all", "ausgewaehlt": "selected", "nur_github": "local_only"}.get(allowed, "selected")}
    if a.get("sha_pinning", False):
        perm["sha_pinning_required"] = True

    def check_perm():
        cur = _gh(f"repos/{repo}/actions/permissions")
        if cur.get("allowed_actions") != perm["allowed_actions"] or (perm.get("sha_pinning_required") and not cur.get("sha_pinning_required")):
            rep.do(f"Actions: erlaubte Actions «{allowed}»" + (", SHA-Pinning Pflicht" if perm.get("sha_pinning_required") else ""))
            if not rep.dry:
                _gh("-X", "PUT", f"repos/{repo}/actions/permissions", input_json=perm)
        if perm["allowed_actions"] == "selected":
            sel = {"github_owned_allowed": True, "verified_allowed": bool(a.get("verifizierte_erlauben", True)),
                   "patterns_allowed": list(a.get("zusaetzlich_erlaubt", []))}
            cur_sel = _gh(f"repos/{repo}/actions/permissions/selected-actions")
            if cur_sel != sel:
                rep.do(f"Actions-Richtlinie: GitHub-eigene{' + verifizierte' if sel['verified_allowed'] else ''} Actions"
                       + (f" + {', '.join(sel['patterns_allowed'])}" if sel["patterns_allowed"] else ""))
                if not rep.dry:
                    _gh("-X", "PUT", f"repos/{repo}/actions/permissions/selected-actions", input_json=sel)
    _try(rep, "Actions-Richtlinie", check_perm)

    def check_workflow():
        cur = _gh(f"repos/{repo}/actions/permissions/workflow")
        want = {"default_workflow_permissions": "write", "can_approve_pull_request_reviews": False}
        if any(cur.get(k) != v for k, v in want.items()):
            rep.do("Actions: Workflow-Rechte «Read and write», Workflows dürfen keine Pull Requests genehmigen")
            if not rep.dry:
                _gh("-X", "PUT", f"repos/{repo}/actions/permissions/workflow", input_json=want)
    _try(rep, "Actions-Workflow-Rechte", check_workflow)

    days = int(_auto(a.get("aufbewahrung_tage", "auto"), public, 90, 30))

    def check_retention():
        cur = _gh(f"repos/{repo}/actions/permissions/artifact-and-log-retention")
        if cur.get("days") != days:
            rep.do(f"Actions: Artefakte und Protokolle {days} Tage aufbewahren")
            if not rep.dry:
                _gh("-X", "PUT", f"repos/{repo}/actions/permissions/artifact-and-log-retention", input_json={"days": days})
    _try(rep, "Aufbewahrung Artefakte/Protokolle", check_retention)

    if public:
        policy = a.get("fork_freigabe", "all_external_contributors")

        def check_fork():
            cur = _gh(f"repos/{repo}/actions/permissions/fork-pr-contributor-approval")
            if cur.get("approval_policy") != policy:
                rep.do(f"Actions: Workflows aus Forks brauchen Freigabe ({policy})")
                if not rep.dry:
                    _gh("-X", "PUT", f"repos/{repo}/actions/permissions/fork-pr-contributor-approval", input_json={"approval_policy": policy})
        _try(rep, "Freigabe für Fork-Workflows", check_fork)

    oidc = a.get("oidc_claims", [])

    def check_oidc():
        cur = _gh(f"repos/{repo}/actions/oidc/customization/sub")
        want = {"use_default": True} if not oidc else {"use_default": False, "include_claim_keys": list(oidc)}
        if bool(cur.get("use_default")) != want["use_default"] or (oidc and cur.get("include_claim_keys") != oidc):
            rep.do("OIDC: " + ("Standard-Subject" if want["use_default"] else f"Subject aus {', '.join(oidc)}"))
            if not rep.dry:
                _gh("-X", "PUT", f"repos/{repo}/actions/oidc/customization/sub", input_json=want)
    _try(rep, "OIDC-Subject", check_oidc)


# --- Umgebungen ------------------------------------------------------------------------------------------------

def environments(cfg: dict, repo: str, rep, owner_id: int | None) -> None:
    for env in cfg.get("umgebungen", []):
        name = env["name"]

        def apply_env(env=env, name=name):
            existing = {e["name"] for e in (_gh(f"repos/{repo}/environments") or {}).get("environments", [])}
            if name in existing:
                return
            body: dict = {"wait_timer": int(env.get("wartezeit", 0)), "prevent_self_review": False}
            if env.get("pruefer") and owner_id:
                body["reviewers"] = [{"type": "User", "id": owner_id}]
            refs = [("branch", b) for b in env.get("nur_branches", [])] + [("tag", t) for t in env.get("nur_tags", [])]
            if refs:
                body["deployment_branch_policy"] = {"protected_branches": False, "custom_branch_policies": True}
            rep.do(f"Umgebung «{name}»" + (" mit Freigabe" if body.get("reviewers") else "")
                   + (f", nur {', '.join(r for _, r in refs)}" if refs else ""))
            if rep.dry:
                return
            _gh("-X", "PUT", f"repos/{repo}/environments/{quote(name)}", input_json=body)
            for kind, ref in refs:
                _gh("-X", "POST", f"repos/{repo}/environments/{quote(name)}/deployment-branch-policies", input_json={"name": ref, "type": kind})
        _try(rep, f"Umgebung «{name}» (Freigaben in privaten Repositorys nur mit kostenpflichtigem Plan)", apply_env)


# --- Webhooks --------------------------------------------------------------------------------------------------

def webhooks(cfg: dict, repo: str, rep) -> None:
    hooks = cfg.get("webhooks", [])
    if not hooks:
        return

    def apply_hooks():
        existing = {h["config"].get("url") for h in _gh(f"repos/{repo}/hooks") or []}
        for h in hooks:
            if h["url"] in existing:
                continue
            secret = os.environ.get(h.get("secret_env", ""), "") if h.get("secret_env") else ""
            if h.get("secret_env") and not secret:
                rep.warn(f"Webhook {h['url']}: Umgebungsvariable {h['secret_env']} für das Geheimnis fehlt – nicht angelegt")
                continue
            rep.do(f"Webhook {h['url']} ({', '.join(h.get('ereignisse', ['push']))})")
            if not rep.dry:
                conf = {"url": h["url"], "content_type": "json", "insecure_ssl": "0"}
                if secret:
                    conf["secret"] = secret
                _gh("-X", "POST", f"repos/{repo}/hooks", input_json={"name": "web", "active": True, "events": h.get("ereignisse", ["push"]), "config": conf})
    _try(rep, "Webhooks", apply_hooks)


# --- Pages -----------------------------------------------------------------------------------------------------

def pages(cfg: dict, repo: str, rep) -> None:
    p = cfg.get("pages", {})
    if not p.get("aktiv", False):
        return

    def apply_pages():
        r = subprocess.run(["gh", "api", f"repos/{repo}/pages", "--silent"], capture_output=True, text=True)
        if r.returncode == 0:
            return
        rep.do("GitHub Pages eingeschaltet (Quelle: GitHub Actions)")
        if not rep.dry:
            _gh("-X", "POST", f"repos/{repo}/pages", input_json={"build_type": "workflow"})
    _try(rep, "GitHub Pages (in privaten Repositorys nur mit kostenpflichtigem Plan)", apply_pages)


# --- Advanced Security -----------------------------------------------------------------------------------------

def codeql_workflow(cfg: dict, public: bool, root: Path | None) -> bool:
    """Übernimmt der Workflow codeql-erweitert.yml das Code Scanning (Funde als Issues)? Dann darf das
    Standard-Setup nicht eingeschaltet sein – GitHub lehnt sonst die Ergebnisse des Workflows ab."""
    mode = cfg.get("codeql", {}).get("workflow", "auto")
    if mode is True:
        return True
    if mode is not True and mode != "auto":
        return False
    if not _auto(cfg.get("sicherheit", {}).get("code_scanning", "auto"), public, True, False):
        return False
    folder = (root or Path(".")) / ".github" / "workflows"
    if not (folder / "codeql-erweitert.yml").exists():
        return False
    return not any("github/codeql-action/analyze" in p.read_text(encoding="utf-8", errors="replace")
                   for p in folder.glob("*.y*ml") if p.name != "codeql-erweitert.yml")


def security(cfg: dict, repo: str, rep, public: bool, current: dict, root: Path | None = None) -> None:
    s = cfg.get("sicherheit", {})

    if s.get("dependabot_warnungen", True):
        def alerts():
            r = subprocess.run(["gh", "api", f"repos/{repo}/vulnerability-alerts", "--silent"], capture_output=True, text=True)
            if r.returncode != 0:
                rep.do("Dependabot-Warnungen eingeschaltet")
                if not rep.dry:
                    _gh("-X", "PUT", f"repos/{repo}/vulnerability-alerts")
        _try(rep, "Dependabot-Warnungen", alerts)

    if s.get("dependabot_sicherheitsupdates", True):
        def fixes():
            cur = _gh(f"repos/{repo}/automated-security-fixes")
            if not cur.get("enabled"):
                rep.do("Dependabot-Sicherheitsupdates eingeschaltet")
                if not rep.dry:
                    _gh("-X", "PUT", f"repos/{repo}/automated-security-fixes")
        _try(rep, "Dependabot-Sicherheitsupdates", fixes)

    if codeql_workflow(cfg, public, root):
        def codeql_off():
            cur = _gh(f"repos/{repo}/code-scanning/default-setup")
            if cur.get("state") == "configured":
                rep.do("Code Scanning: Standard-Setup ausgeschaltet – der Workflow «CodeQL erweitert» übernimmt (Funde als Issues)")
                if not rep.dry:
                    _gh("-X", "PATCH", f"repos/{repo}/code-scanning/default-setup", input_json={"state": "not-configured"})
        _try(rep, "Code Scanning (Workflow «CodeQL erweitert»)", codeql_off)
    elif _auto(s.get("code_scanning", "auto"), public, True, False):
        def codeql():
            cur = _gh(f"repos/{repo}/code-scanning/default-setup")
            if cur.get("state") != "configured":
                rep.do("Code Scanning (CodeQL, Standard-Setup) eingeschaltet")
                if not rep.dry:
                    _gh("-X", "PATCH", f"repos/{repo}/code-scanning/default-setup", input_json={"state": "configured", "query_suite": "default"})
        _try(rep, "Code Scanning (privat nur mit GitHub Advanced Security)", codeql)

    if public and s.get("private_meldungen", True):
        def pvr():
            cur = _gh(f"repos/{repo}/private-vulnerability-reporting")
            if not cur.get("enabled"):
                rep.do("Private Sicherheitsmeldungen («Report a vulnerability») eingeschaltet")
                if not rep.dry:
                    _gh("-X", "PUT", f"repos/{repo}/private-vulnerability-reporting")
        _try(rep, "Private Sicherheitsmeldungen", pvr)


# --- Deploy-Keys -----------------------------------------------------------------------------------------------

def deploy_keys(cfg: dict, repo: str, rep, root: Path) -> list[str]:
    """Vorgesehene Deploy-Keys: mit öffentlichem Schlüssel (Datei) anlegen, sonst als offener Punkt melden."""
    todo = []
    keys = cfg.get("deploy_keys", [])
    if not keys:
        return todo
    try:
        existing = {k["title"] for k in _gh(f"repos/{repo}/keys") or []}
    except RuntimeError as e:
        rep.warn(f"Deploy-Keys nicht lesbar ({e})")
        return todo
    for k in keys:
        if k["titel"] in existing:
            continue
        pub = k.get("oeffentlicher_schluessel", "")
        pub = os.path.expanduser(pub) if pub else ""
        path = (root / pub) if pub and not os.path.isabs(pub) else Path(pub) if pub else None
        if path and path.exists():
            rep.do(f"Deploy-Key «{k['titel']}» ({'nur lesen' if k.get('nur_lesen', True) else 'schreiben'}) angelegt")
            if not rep.dry:
                _gh("-X", "POST", f"repos/{repo}/keys", input_json={"title": k["titel"], "key": path.read_text().strip(), "read_only": bool(k.get("nur_lesen", True))})
        else:
            slug = k["titel"].lower().replace(" ", "-")
            todo.append(f"Deploy-Key «{k['titel']}» ({k.get('zweck', '')}): ssh-keygen -t ed25519 -N '' -C '{repo} {k['titel']}' -f ~/.ssh/{slug} "
                        f"→ öffentlichen Teil eintragen: gh repo deploy-key add ~/.ssh/{slug}.pub -R {repo} -t '{k['titel']}'"
                        + ("" if k.get("nur_lesen", True) else " -w") + " (privaten Teil nur dort hinterlegen, wo er gebraucht wird)")
    return todo


# --- Secrets und Variablen -------------------------------------------------------------------------------------

def variables(cfg: dict, repo: str, rep) -> None:
    for v in cfg.get("variablen", []):
        scope = v.get("bereich", "actions")

        def apply_var(v=v, scope=scope):
            base = f"repos/{repo}/environments/{quote(scope.split(':', 1)[1])}/variables" if scope.startswith("umgebung:") else f"repos/{repo}/actions/variables"
            names = {x["name"] for x in (_gh(f"{base}?per_page=100") or {}).get("variables", [])}
            if v["name"] in names:
                return
            rep.do(f"Variable {v['name']} ({scope}) = «{v.get('wert', '')}»")
            if not rep.dry:
                _gh("-X", "POST", base, input_json={"name": v["name"], "value": str(v.get("wert", ""))})
        _try(rep, f"Variable {v['name']}", apply_var)


def secrets(cfg: dict, repo: str, rep) -> list[str]:
    todo = []
    placeholder = bool(cfg.get("secrets_einstellungen", {}).get("platzhalter", True))
    wanted = list(cfg.get("secrets", []))
    if cfg.get("release_dateien", {}).get("virustotal", False) and not any(x.get("name") == "VIRUSTOTAL_API_KEY" for x in wanted):
        wanted.append({"name": "VIRUSTOTAL_API_KEY", "bereich": "actions",
                       "beschreibung": "API-Schlüssel von virustotal.com (kostenloses Konto) für die Prüfung der Release-Dateien"})
    for s in wanted:
        scope = s.get("bereich", "actions")
        name = s["name"]
        if scope.startswith("umgebung:"):
            env = scope.split(":", 1)[1]
            list_path, args = f"repos/{repo}/environments/{quote(env)}/secrets", ["--env", env]
        elif scope == "agents":
            list_path, args = f"repos/{repo}/environments/copilot/secrets", ["--env", "copilot"]
        else:
            list_path = f"repos/{repo}/{ {'actions': 'actions', 'codespaces': 'codespaces', 'dependabot': 'dependabot'}.get(scope, 'actions') }/secrets"
            args = ["--app", scope if scope in ("actions", "codespaces", "dependabot") else "actions"]
        try:
            names = {x["name"] for x in (_gh(f"{list_path}?per_page=100") or {}).get("secrets", [])}
        except RuntimeError as e:
            rep.warn(f"Secrets {scope} nicht lesbar ({str(e)[:120]})")
            continue
        if name in names:
            continue
        value = os.environ.get(name, "")
        cmd = ["gh", "secret", "set", name, "-R", repo, *args]
        if value or placeholder:
            rep.do(f"Secret {name} ({scope}) " + ("aus Umgebungsvariable gesetzt" if value else f"mit Platzhalter «{PLACEHOLDER}» angelegt – bitte ersetzen"))
            if not rep.dry:
                r = subprocess.run([*cmd, "--body", value or PLACEHOLDER], capture_output=True, text=True)
                if r.returncode != 0:
                    rep.warn(f"Secret {name}: {r.stderr.strip()[:160]}")
        if not value:
            todo.append(f"Secret {name} ({scope}{', ' + s['beschreibung'] if s.get('beschreibung') else ''}): {' '.join(cmd)}  (Wert wird abgefragt)")
    return todo


def apply_advanced(cfg: dict, repo: str, rep, public: bool, current: dict, root: Path) -> list[str]:
    owner_id = (current.get("owner") or {}).get("id")
    actions(cfg, repo, rep, public)
    environments(cfg, repo, rep, owner_id)
    webhooks(cfg, repo, rep)
    pages(cfg, repo, rep)
    security(cfg, repo, rep, public, current, root)
    variables(cfg, repo, rep)
    todo = secrets(cfg, repo, rep)
    todo += deploy_keys(cfg, repo, rep, root)
    return todo
