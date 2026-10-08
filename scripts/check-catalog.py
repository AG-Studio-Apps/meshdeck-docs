#!/usr/bin/env python3
"""The catalogue gates (plan-s4-templates.md 4.3). Run by the publish workflow's build job (no
secrets) and by test-templates.yml; run it locally before committing a catalogue change.

    scripts/check-catalog.py                                  # every offline gate on templates.json
    scripts/check-catalog.py --deployed-ref origin/main       # + the version gate against that commit
    scripts/check-catalog.py --deployed-ref github --live --risk --summary "$GITHUB_STEP_SUMMARY"
    scripts/check-catalog.py --site _site                     # the built site, after Jekyll
    scripts/check-catalog.py --self-test                      # the gates' own tests (fixtures included)

Gates, in order (any FAIL exits 1):
  load            UTF-8, no BOM, valid JSON, no duplicate keys, no NaN.
  meshdeck-1.0.2  fielded meshDeck v1.0.2 decodes the WHOLE file (its decoder is synthesized:
                  one bad template empties every phone's list). Mirror pinned by fixtures.
  schema          known keys only, integers as integers, `kind` from the shared enum, options and
                  credential and generate shapes, unique ids and categories, featured ids exist,
                  every template's category listed.
  template-rules  shared-1.4.0 StackTemplate.validate(): id a stack name, non-empty fields,
                  env-name keys, no duplicate keys, every ${VAR} without a default declared.
  app-sanity      meshTerm's TemplateSanity: display caps; control, separator and bidi
                  characters; rule 21 (every placeholder declared, braced, bare and inside
                  default or option values; no session or COMPOSE_/DOCKER_/... keys, upper-cased);
                  YAML numeric escapes; the compose refusals (include, name, extends file,
                  driver_opts device, secrets/configs file or environment, and the R10 forms that
                  carry them: aliases, merge keys, flow documents, explicit and tagged keys, ---).
  text            no app name in any template text, no em-dash or en-dash in display text, no
                  published default on a secret.
  version         against the DEPLOYED commit: unchanged, or exactly deployed + 1; a changed
                  template bumps its own version; a live version above this one, or the same
                  version with other bytes, is an ALARM.
  repo            no secret key material tracked; keys/ holds exactly the two public keys with
                  distinct ids; Jekyll excludes scripts/ and keys/; a committed
                  templates.json.minisig must be a valid EMERGENCY signature of this version.
  risk            (--risk) each added or changed template resolves with `docker compose config
                  --format json`; the summary lists its host-facing features and the delta.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import catalog_compat as compat  # noqa: E402
import catalog_risk as risk  # noqa: E402
import catalog_sanity as sanity  # noqa: E402
import catalog_signature as signature  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, ".."))
CATALOG = os.path.join(REPO, "templates.json")
LIVE_URL = signature.DEFAULT_URL
PIPELINE_PATHS = (".github", "scripts", "keys", "_config.yml")
FIXTURES = os.path.join(HERE, "fixtures", "meshdeck-v1.0.2")


class Gate:
    def __init__(self, name):
        self.name, self.status, self.messages, self.notes = name, "PASS", [], []

    def fail(self, message):
        self.status = "FAIL"
        self.messages.append(message)

    def skip(self, message):
        if self.status == "PASS":
            self.status = "SKIP"
        self.notes.append(message)

    def note(self, message):
        self.notes.append(message)


def git(*args, check=True):
    result = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {result.stderr.decode(errors='replace').strip()}")
    return result


def deployed_commit_from_github():
    """The commit of the newest github-pages deployment that succeeded (legacy builds and this
    workflow both record one)."""
    api = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ.get("GITHUB_TOKEN", "")

    def get(path):
        request = urllib.request.Request(f"{api}/repos/{repo}/{path}", headers={
            "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"})
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)

    for deployment in get("deployments?environment=github-pages&per_page=50"):
        statuses = get(f"deployments/{deployment['id']}/statuses?per_page=100")
        if any(status.get("state") == "success" for status in statuses):
            return deployment["sha"]
    raise RuntimeError("no successful github-pages deployment found")


def resolve_ref(ref):
    if ref == "github":
        ref = deployed_commit_from_github()
    if git("cat-file", "-e", f"{ref}^{{commit}}", check=False).returncode != 0:
        git("fetch", "--no-tags", "--depth=1", "origin", ref)
    return git("rev-parse", f"{ref}^{{commit}}").stdout.decode().strip()


def read_at(ref, path):
    result = git("show", f"{ref}:{path}", check=False)
    return result.stdout if result.returncode == 0 else None


def fetch_live(url):
    return signature.fetch_live(url)


# --- Gates ------------------------------------------------------------------------------

def well_formed_templates(doc):
    """Templates the per-template gates can read (the others already failed meshdeck/schema)."""
    out = []
    for template in doc.get("templates") or []:
        if isinstance(template, dict) and compat.meshdeck_v102_problem(
                {"version": 1, "categories": [], "templates": [template]}) is None:
            out.append(template)
    return out


def gate_templates(doc, gates):
    rules, app, text = gates
    for template in well_formed_templates(doc):
        tid = template["id"]
        for issue in sanity.validate(template):
            rules.fail(f"{tid}: {issue}")
        for problem in sanity.problems(template):
            if not problem.startswith("invalid: "):
                app.fail(f"{tid}: {problem}")
        for problem in sanity.catalogue_rules(template):
            text.fail(f"{tid}: {problem}")
    for category in doc.get("categories") or []:
        if isinstance(category, str):
            if sanity.has_control_characters(category, False):
                app.fail(f"category {category!r} has a control, separator or bidirectional formatting character")
            if len(category) > sanity.CATEGORY_LIMIT:
                app.fail(f"category {category!r} is longer than {sanity.CATEGORY_LIMIT} characters")
            for dash, word in sanity.DASHES.items():
                if dash in category:
                    text.fail(f"category {category!r} has an {word}")


_MD_SPECIAL = set("\\`*_{}[]()#+-.!|~<>&")


def md(value):
    """Template-derived text, made inert for the Markdown summary the signer reads: every Markdown
    or HTML special character escaped or encoded and line breaks flattened, so a bind target like
    `/data<!--` or `**removed**` cannot hide or forge lines of the summary."""
    out = []
    for ch in str(value):
        if ch in "\r\n\u2028\u2029\u0085":
            out.append(" ")
        elif ch == "<":
            out.append("&lt;")
        elif ch == ">":
            out.append("&gt;")
        elif ch == "&":
            out.append("&amp;")
        elif ch in _MD_SPECIAL:
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def canonical(template):
    return json.dumps(template, sort_keys=True, ensure_ascii=False)


def template_changes(old_doc, new_doc):
    old = {t["id"]: t for t in old_doc.get("templates", []) if isinstance(t, dict) and "id" in t}
    new = {t["id"]: t for t in new_doc.get("templates", []) if isinstance(t, dict) and "id" in t}
    added = [i for i in new if i not in old]
    removed = [i for i in old if i not in new]
    changed = [i for i in new if i in old and canonical(old[i]) != canonical(new[i])]
    return old, new, added, removed, changed


def gate_version(gate, raw, doc, deployed_raw, live):
    version = doc.get("version")
    if not isinstance(version, int):
        gate.fail("no integer version to check")
        return
    if deployed_raw is None:
        gate.skip("no deployed commit given (--deployed-ref): monotonic check not run")
    else:
        try:
            deployed = json.loads(deployed_raw)
            deployed_version = deployed["version"]
        except (ValueError, KeyError, TypeError):
            gate.fail("the deployed templates.json does not parse")
            return
        if deployed_raw == raw:
            gate.note(f"templates.json is unchanged since the deployed commit (version {version})")
        elif version == deployed_version:
            gate.fail(f"templates.json changed but the version is still {version}: the apps refuse the same "
                      f"version with different bytes. Set it to {deployed_version + 1}.")
        elif version != deployed_version + 1:
            gate.fail(f"version {version}: it must be exactly the deployed version + 1 = {deployed_version + 1}")
        else:
            gate.note(f"version {deployed_version} -> {version}")
        if deployed_raw != raw:
            old, new, _, _, changed = template_changes(deployed, doc)
            for tid in changed:
                ov, nv = old[tid].get("version"), new[tid].get("version")
                if not (isinstance(ov, int) and isinstance(nv, int) and nv > ov):
                    gate.fail(f"{tid} changed but its own version did not go up ({ov} -> {nv})")
    if live is None:
        return
    live_raw, live_error = live
    if live_error:
        gate.note(f"the live catalogue could not be read ({live_error}); live checks skipped")
        return
    try:
        live_version = json.loads(live_raw)["version"]
    except (ValueError, KeyError, TypeError):
        gate.fail("ALARM: the live templates.json does not parse")
        return
    if isinstance(live_version, int) and live_version > version:
        gate.fail(f"ALARM: the live site serves version {live_version}, above this repository's {version}. "
                  f"The hosting is serving something this repository never published. Investigate before "
                  f"publishing anything.")
    elif live_version == version and live_raw != raw:
        gate.fail(f"the live site already serves a DIFFERENT version {version}; devices that cached it would "
                  f"refuse this one. Bump the version.")
    else:
        gate.note(f"live: version {live_version}")


SECRET_FIRST_LINE = re.compile(rb"secret key", re.IGNORECASE)
STRAY_NAME = re.compile(r"(\.key$|\.age$|passphrase)", re.IGNORECASE)


def gate_repo(gate, version):
    tracked = git("ls-files", "-z").stdout.decode().split("\0")
    for path in filter(None, tracked):
        full = os.path.join(REPO, path)
        if STRAY_NAME.search(os.path.basename(path)):
            gate.fail(f"{path}: a file named like key material is tracked")
        if os.path.isfile(full):
            with open(full, "rb") as handle:
                first = handle.read(256).split(b"\n", 1)[0]
            if SECRET_FIRST_LINE.search(first):
                gate.fail(f"{path}: looks like a minisign SECRET key (first line {first[:80]!r})")
    keys_dir = os.path.join(REPO, "keys")
    present = sorted(os.listdir(keys_dir)) if os.path.isdir(keys_dir) else []
    if present != ["catalog-emergency.pub", "catalog-primary.pub"]:
        gate.fail(f"keys/ must hold exactly catalog-primary.pub and catalog-emergency.pub, found {present}")
    else:
        try:
            ids = signature.roster(keys_dir)
            gate.note("keys: " + ", ".join(f"{role} {kid}" for role, (_, kid) in sorted(ids.items())))
        except (signature.PairError, ValueError) as error:
            gate.fail(f"keys/: {error}")
    with open(os.path.join(REPO, "_config.yml"), encoding="utf-8") as handle:
        config = handle.read()
    match = re.search(r"^exclude:\s*\n((?:[ \t]+-[^\n]*\n?)+)", config, re.M)
    excluded = {line.strip().lstrip("-").strip().strip("\"'") for line in (match.group(1).splitlines() if match else [])}
    for needed in ("scripts", "keys"):
        if needed not in excluded:
            gate.fail(f"_config.yml must exclude {needed}/ from the site")
    committed = os.path.join(REPO, "templates.json.minisig")
    if os.path.exists(committed):
        if not shutil.which("minisign"):
            gate.skip("minisign is not installed: the committed emergency signature was not verified")
            return
        try:
            with open(CATALOG, "rb") as body, open(committed, "rb") as sig:
                signer, signed, comment = signature.check_pair(body.read(), sig.read(), "emergency", version)
            gate.note(f"committed EMERGENCY signature verifies ({comment})")
        except (signature.PairError, OSError) as error:
            gate.fail(f"templates.json.minisig is committed but is not a valid emergency signature of this "
                      f"catalogue ({error}). After an emergency publish, delete it in the next catalogue change.")


def check_site(site):
    problems = []
    with open(CATALOG, "rb") as a:
        source = a.read()
    built = os.path.join(site, "templates.json")
    if not os.path.isfile(built):
        problems.append("the built site has no templates.json")
    else:
        with open(built, "rb") as b:
            if b.read() != source:
                problems.append("Jekyll changed templates.json (the built bytes differ from the commit)")
    for name in ("scripts", "keys", ".github"):
        if os.path.exists(os.path.join(site, name)):
            problems.append(f"the built site contains {name}/ (exclude it in _config.yml)")
    for root, _, files in os.walk(site):
        for name in files:
            if name.endswith((".py", ".sh", ".pub", ".key", ".age")):
                problems.append(f"the built site contains {os.path.relpath(os.path.join(root, name), site)}")
    committed = os.path.join(REPO, "templates.json.minisig")
    built_sig = os.path.join(site, "templates.json.minisig")
    if os.path.exists(built_sig) and not os.path.exists(committed):
        problems.append("the built site has a templates.json.minisig that is not committed")
    return problems


# --- Risk -------------------------------------------------------------------------------

def risk_report(gate, deployed_doc, doc, compose_cmd):
    """Markdown lines for the summary; FAILs the gate when a new or changed template does not resolve."""
    lines = []
    old, new, added, removed, changed = template_changes(deployed_doc or {"templates": []}, doc)
    targets = [(tid, "added") for tid in added] + [(tid, "changed") for tid in changed]
    if not targets:
        return ["No template was added or changed, so there are no risk deltas."]
    readable = {t["id"] for t in well_formed_templates(doc)}
    unchanged = []
    for tid, kind in targets:
        if tid not in readable:
            continue
        template = new[tid]
        if sanity.refusals(template["compose"]):
            gate.fail(f"{tid}: not resolved (its compose uses a refused form; see app-sanity)")
            continue
        try:
            now = risk.template_features(template, compose_cmd)
        except risk.ResolveError as error:
            gate.fail(f"{tid}: {error}")
            continue
        before, baseline = set(), ""
        if kind == "changed":
            previous = old[tid]
            if not isinstance(previous, dict) or sanity.refusals(previous.get("compose", "")):
                baseline = " (the deployed version could not be resolved safely, so everything is listed)"
            else:
                try:
                    before = risk.template_features(previous, compose_cmd)
                except (risk.ResolveError, KeyError, TypeError):
                    baseline = " (the deployed version did not resolve, so everything is listed)"
        gained = sorted(now - before)
        lost = sorted(before - now)
        if not gained and not lost and not baseline:
            unchanged.append(tid)
            continue
        version = f"v{old[tid].get('version')} -> v{template['version']}" if kind == "changed" else f"v{template['version']}"
        lines.append(f"**{md(tid)}** ({kind}, {md(version)}){baseline}")
        for text, strong in gained:
            lines.append(f"- {'**NEW**' if strong else 'new'}: {md(text)}")
        for text, _ in lost:
            lines.append(f"- removed: {md(text)}")
        lines.append("")
    if unchanged:
        lines.append(f"No change in what these ask of the host: {', '.join(md(t) for t in unchanged)}.")
    return lines


# --- Run --------------------------------------------------------------------------------

def run(args):
    gates = {name: Gate(name) for name in
             ("load", "meshdeck-1.0.2", "schema", "template-rules", "app-sanity", "text", "version", "repo", "risk")}
    with open(args.catalog, "rb") as handle:
        raw = handle.read()
    summary = []
    try:
        doc = compat.strict_load(raw)
    except compat.LoadError as error:
        gates["load"].fail(str(error))
        doc = None
    deployed_sha, deployed_raw, deployed_doc, banner = None, None, None, []
    if args.deployed_ref:
        try:
            deployed_sha = resolve_ref(args.deployed_ref)
            deployed_raw = read_at(deployed_sha, "templates.json")
            if deployed_raw is None:
                gates["version"].fail(f"the deployed commit {deployed_sha[:12]} has no templates.json")
            else:
                deployed_doc = json.loads(deployed_raw)
            banner = [p for p in git("diff", "--name-only", deployed_sha, "HEAD", "--", *PIPELINE_PATHS)
                      .stdout.decode().splitlines() if p]
        except (RuntimeError, KeyError, urllib.error.URLError, ValueError) as error:
            gates["version"].fail(f"cannot read the deployed commit: {error}")
    live = None
    if args.live:
        try:
            live_raw, _ = fetch_live(args.live_url)
            live = (live_raw, None)
        except (urllib.error.URLError, OSError, signature.PairError) as error:
            live = (None, str(error))

    if doc is not None:
        problem = compat.meshdeck_v102_problem(json.loads(raw))
        if problem:
            gates["meshdeck-1.0.2"].fail(f"meshDeck v1.0.2 cannot decode this file, so it would show NO hosted "
                                         f"templates: {problem}")
        for message in compat.schema_problems(doc):
            gates["schema"].fail(message)
        gate_templates(doc, (gates["template-rules"], gates["app-sanity"], gates["text"]))
        gate_version(gates["version"], raw, doc, deployed_raw, live)
        gate_repo(gates["repo"], doc.get("version"))
        if args.risk:
            compose_cmd = tuple(args.compose.split())
            summary_risk = risk_report(gates["risk"], deployed_doc, doc, compose_cmd)
        else:
            gates["risk"].skip("not run (--risk)")
            summary_risk = []
    else:
        for name in gates:
            if name != "load":
                gates[name].skip("not run: the file does not load")
        summary_risk = []

    # Report.
    failed = [g for g in gates.values() if g.status == "FAIL"]
    version = doc.get("version") if isinstance(doc, dict) else "?"
    deployed_version = deployed_doc.get("version") if isinstance(deployed_doc, dict) else None
    title = f"Catalogue v{deployed_version} -> v{version}" if deployed_version is not None else f"Catalogue v{version}"
    if deployed_raw is not None and deployed_raw == raw:
        title = f"Catalogue v{version} (unchanged)"
    summary.append(f"## {title}")
    summary.append("")
    if banner and not args.no_banner:
        summary.append("> [!WARNING]")
        summary.append("> **This push changes the publishing pipeline itself** (" + ", ".join(md(p) for p in banner)
                       + "). This summary is produced by that code, so it cannot vouch for itself. Before "
                       "approving the signing job, read the commit diff on github.com, not this page.")
        summary.append("")
    if deployed_sha:
        summary.append(f"Deployed commit: `{deployed_sha[:12]}` (v{deployed_version}). This commit: "
                       f"`{git('rev-parse', 'HEAD').stdout.decode().strip()[:12]}`.")
    if live is not None:
        summary.append(f"Live site: {('version ' + md(json.loads(live[0]).get('version'))) if live[0] else 'unreadable (' + md(live[1]) + ')'}.")
    summary.append("")
    summary.append("| Gate | Result | Detail |")
    summary.append("|---|---|---|")
    for gate in gates.values():
        detail = md("; ".join(gate.messages[:3] + gate.notes[:2]))
        if len(gate.messages) > 3:
            detail += f"; and {len(gate.messages) - 3} more"
        summary.append(f"| {gate.name} | {gate.status} | {detail} |")
    summary.append("")
    if doc is not None and deployed_doc is not None and deployed_raw != raw:
        old, new, added, removed, changed = template_changes(deployed_doc, doc)
        summary.append("### Templates")
        summary.append("")
        summary.append(f"- added ({len(added)}): " + (", ".join(f"{md(i)} v{md(new[i].get('version'))}" for i in added) or "none"))
        summary.append(f"- removed ({len(removed)}): " + (", ".join(md(i) for i in removed) or "none"))
        summary.append(f"- changed ({len(changed)}): " + (", ".join(
            f"{md(i)} v{md(old[i].get('version'))} -> v{md(new[i].get('version'))}" for i in changed) or "none"))
        summary.append("")
    if summary_risk:
        summary.append("### What changed templates ask of the host")
        summary.append("")
        summary.append("From `docker compose config --format json` with dummy values (anchors, merges, `extends` "
                       "and interpolation applied). **NEW** marks the features that matter most.")
        summary.append("")
        summary += summary_risk
    if failed:
        summary.append("### Failures")
        summary.append("")
        for gate in failed:
            for message in gate.messages:
                summary.append(f"- **{gate.name}**: {md(message)}")
        summary.append("")

    text = "\n".join(summary) + "\n"
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as handle:
            handle.write(text)
    for gate in gates.values():
        print(f"{gate.status:4}  {gate.name}")
        for message in gate.messages:
            print(f"      - {message}")
        for note in gate.notes:
            print(f"      . {note}")
    if summary_risk and not args.summary:
        print("\nRisk deltas:")
        print("\n".join(summary_risk))
    return 1 if failed else 0


# --- Self-test --------------------------------------------------------------------------

BASE_TEMPLATE = {
    "id": "demo", "name": "Demo", "tagline": "A demo app", "category": "Tools", "symbol": "shippingbox",
    "version": 1, "compose": "services:\n  app:\n    image: nginx\n    ports:\n      - \"${PORT}:80\"\n",
    "variables": [{"key": "PORT", "label": "Port", "defaultValue": "8080", "isSecret": False, "isPreset": False}],
    "notes": [],
}


def _template(**changes):
    template = json.loads(json.dumps(BASE_TEMPLATE))
    template.update(changes)
    return template


def _with_compose(compose, variables=None):
    return _template(compose=compose, variables=variables if variables is not None else [])


def _var(key, default="", secret=False, preset=False, **extra):
    variable = {"key": key, "label": key.title(), "defaultValue": default, "isSecret": secret, "isPreset": preset}
    variable.update(extra)
    return variable


SANITY_CASES = [
    # (name, template, expected substring in problems() or None for clean)
    ("base passes", _template(), None),
    ("one-line JSON document", _with_compose('{"include": ["x.yml"], "services": {}}\n'), "'{'"),
    ("top-level include", _with_compose("include:\n  - x.yml\nservices:\n  a:\n    image: x\n"), "'include'"),
    ("top-level name", _with_compose("name: other\nservices:\n  a:\n    image: x\n"), "'name'"),
    ("top-level merge key", _with_compose("x: &b\n  include: [y]\n<<: *b\nservices:\n  a:\n    image: x\n"), "'<<'"),
    ("extends file block", _with_compose("services:\n  a:\n    extends:\n      file: x.yml\n      service: b\n"), "'extends'"),
    ("extends file flow", _with_compose("services:\n  a:\n    extends: {file: x.yml, service: b}\n"), "'extends'"),
    ("extends alias", _with_compose("x: &e {file: x.yml, service: b}\nservices:\n  a:\n    extends: *e\n"), "'extends'"),
    ("merge key under extends", _with_compose("x: &e\n  file: x.yml\nservices:\n  a:\n    extends:\n      <<: *e\n      service: b\n"), "'extends'"),
    ("anchored flow value with extends file", _with_compose("services:\n  a: &b {extends: {file: x.yml, service: c}}\n"), "'extends'"),
    ("explicit key", _with_compose("services:\n  a:\n    extends:\n      ? file\n      : x.yml\n"), "'?'"),
    ("tagged key", _with_compose("services:\n  a:\n    !!merge <<: *x\n"), "'!'"),
    ("quoted key with space before colon", _with_compose("services:\n  a:\n    extends:\n      \"file\" : x.yml\n"), "'extends'"),
    ("content after a document marker", _with_compose("--- {include: [x]}\nservices:\n  a:\n    image: x\n"), "'---'"),
    ("YAML directive", _with_compose("%YAML 1.2\nservices:\n  a:\n    image: x\n"), "'---'"),
    ("secrets file block", _with_compose("services:\n  a:\n    image: x\nsecrets:\n  s:\n    file: ./s.txt\n"), "'secrets'"),
    ("secrets file flow", _with_compose("services:\n  a:\n    image: x\nsecrets: {s: {file: ./s.txt}}\n"), "'secrets'"),
    ("secrets alias", _with_compose("x: &s {file: ./s}\nservices:\n  a:\n    image: x\nsecrets:\n  s: *s\n"), "'*'"),
    ("secrets block is an alias", _with_compose("x: &s\n  s:\n    file: ./s\nservices:\n  a:\n    image: x\nsecrets: *s\n"), "'*'"),
    ("configs environment", _with_compose("services:\n  a:\n    image: x\nconfigs:\n  c:\n    environment: HOME\n"), "'configs'"),
    ("volume driver_opts device", _with_compose("services:\n  a:\n    image: x\nvolumes:\n  v:\n    driver_opts:\n      type: none\n      o: bind\n      device: /\n"), "'driver_opts'"),
    ("volume driver_opts alias", _with_compose("x: &o {type: none, o: bind, device: /}\nservices:\n  a:\n    image: x\nvolumes:\n  v:\n    driver_opts: *o\n"), "'*'"),
    ("merge key in volumes", _with_compose("x: &o\n  device: /\nservices:\n  a:\n    image: x\nvolumes:\n  v:\n    <<: *o\n"), "'<<'"),
    ("numeric escape x24", _with_compose('services:\n  a:\n    image: "\\x24{HOME}"\n'), "'\\\\'"),
    ("numeric escape u0024", _with_compose('services:\n  a:\n    image: "\\u0024{HOME}"\n'), "'\\\\'"),
    ("undeclared braced with default", _with_compose("services:\n  a:\n    image: x:${TAG:-latest}\n"), "$TAG"),
    ("undeclared bare", _with_compose("services:\n  a:\n    image: x\n    command: echo $HOME\n"), "$HOME"),
    ("undeclared nested", _with_compose("services:\n  a:\n    image: x:${TAG:-${OTHER}}\n", [_var("TAG", "1")]), "$OTHER"),
    ("escaped dollar is fine", _with_compose("services:\n  a:\n    image: x\n    command: echo $$HOME $${HOME}\n"), None),
    ("placeholder in a default", _with_compose("services:\n  a:\n    image: x:${TAG}\n", [_var("TAG", "${HOME}")]), "$HOME"),
    ("placeholder in an option value", _with_compose("services:\n  a:\n    image: x:${TAG}\n",
                                                     [_var("TAG", "a", options=[{"text": "A", "value": "a"}, {"text": "B", "value": "$HOME"}])]), "$HOME"),
    ("reserved USER", _with_compose("services:\n  a:\n    image: x\n    user: ${USER}\n", [_var("USER", "x")]), "key USER"),
    ("reserved lower-case user", _with_compose("services:\n  a:\n    image: x\n    user: ${user}\n", [_var("user", "x")]), "key user"),
    ("reserved COMPOSE_ prefix", _with_compose("services:\n  a:\n    image: x:${COMPOSE_TAG}\n", [_var("COMPOSE_TAG", "1")]), "COMPOSE_TAG"),
    ("reserved CONTAINER_HOST (S4-U review)", _with_compose("services:\n  a:\n    image: x:${CONTAINER_HOST}\n", [_var("CONTAINER_HOST", "1")]), "CONTAINER_HOST"),
    ("reserved KRB5CCNAME (S4-U review)", _with_compose("services:\n  a:\n    image: x:${KRB5CCNAME}\n", [_var("KRB5CCNAME", "1")]), "KRB5CCNAME"),
    ("reserved PODMAN_ prefix (S4-U review)", _with_compose("services:\n  a:\n    image: x:${PODMAN_X}\n", [_var("PODMAN_X", "1")]), "PODMAN_X"),
    ("SSH_PORT allowed", _with_compose("services:\n  a:\n    image: x\n    ports: ['${SSH_PORT}:22']\n", [_var("SSH_PORT", "2222")]), None),
    ("CONTAINER_NAME allowed", _with_compose("services:\n  a:\n    image: x\n    container_name: ${CONTAINER_NAME}\n", [_var("CONTAINER_NAME", "a")]), None),
    ("service anchors and merge keys are fine", _with_compose("x-base: &base\n  image: x\n  restart: always\nservices:\n  a:\n    <<: *base\n  b:\n    <<: *base\n"), None),
    ("flow mapping in a service is fine", _with_compose("services:\n  a:\n    image: x\n    depends_on:\n      b: { condition: service_healthy }\n  b:\n    image: y\nnetworks: { n: {} }\n"), None),
    ("glob in a command is fine", _with_compose("services:\n  a:\n    image: x\n    command: ls *.txt\n"), None),
    ("block scalar body is not read as keys", _with_compose("configs:\n  c:\n    content: |\n      include: x\n      name: y\nservices:\n  a:\n    image: x\n"), None),
    ("bidi RLO in name", _template(name="Demo\u202e"), "name has a control"),
    ("CRLF in a label", _template(variables=[_var("PORT", "8080", label="a\r\nB=x")]), "label has a control"),
    ("U+2028 in a note", _template(notes=["a\u2028b"]), "a note has a control"),
    ("U+0085 in a tagline", _template(tagline="a\u0085b"), "tagline has a control"),
    ("tab in compose", _with_compose("services:\n  a:\n\timage: x\n"), "compose has a control"),
    ("newline in a note is fine", _template(notes=["line one\nline two"]), None),
    ("accents, emoji and a joiner are fine", _template(name="Caf\u00e9 \U0001f468\u200d\U0001f469"), None),
    ("name over 60", _template(name="x" * 61), "name is longer"),
    ("13 notes", _template(notes=["n"] * 13), "more than 12 notes"),
    ("id not a stack name", _template(id="Demo"), "invalid: id"),
    ("duplicate key", _template(variables=[_var("PORT", "1"), _var("PORT", "2")]), "declared twice"),
]

TEXT_CASES = [
    ("base passes", _template(), None),
    ("em-dash in tagline", _template(tagline="a \u2014 b"), "em-dash"),
    ("en-dash in a note", _template(notes=["4\u20135 GB"]), "en-dash"),
    ("app name in a note", _template(notes=["Open it in meshDeck."]), "names an app"),
    ("app name in compose", _with_compose("services:\n  meshterm:\n    image: x\n"), "names an app"),
    ("app name with a space", _template(tagline="Use Mesh Term"), "names an app"),
    ("mesh terminal is not an app name", _template(tagline="A mesh terminal"), None),
    ("secret default", _template(variables=[_var("PORT", "8080"), _var("DB_PASSWORD", "hunter2", secret=True)]), "published default"),
    ("looksSecret default", _template(variables=[_var("PORT", "8080"), _var("API_TOKEN", "abc")]), "published default"),
    ("preset secret default allowed", _template(variables=[_var("PORT", "8080"), _var("DB_PASSWORD", "x", secret=True, preset=True)]), None),
]


def _doc(version, templates=None):
    return {"version": version, "categories": ["Tools"], "templates": templates or [_template()]}


def _raw(doc):
    return json.dumps(doc, indent=2).encode()


def self_test():
    failures = []

    # 1. The meshDeck mirror against every recorded decode.
    with open(os.path.join(FIXTURES, "expected.json")) as handle:
        recorded = json.load(handle)["decodes"]
    files = sorted(f for f in os.listdir(FIXTURES) if f.endswith(".json") and f != "expected.json")
    if sorted(recorded) != files:
        failures.append(f"fixtures and expected.json disagree on the file list (re-run record-meshdeck-decodes.sh)")
    for name in files:
        with open(os.path.join(FIXTURES, name), encoding="utf-8") as handle:
            answer = compat.mirror_answer_for_text(handle.read())
        if name in recorded and answer != recorded[name]:
            failures.append(f"meshDeck mirror: {name}: mirror says {answer}, meshDeck v1.0.2 says {recorded[name]}")
    print(f"meshDeck v1.0.2 mirror: {len(files)} fixtures checked")

    # 2. The schema layer refuses what the mirror tolerates.
    for label, raw, expect in [
        ("duplicate key", b'{"version": 1, "version": 2}', "duplicate key"),
        ("BOM", b"\xef\xbb\xbf{}", "byte order mark"),
        ("NaN", b'{"version": NaN}', "NaN"),
    ]:
        try:
            compat.strict_load(raw)
            failures.append(f"strict_load accepted {label}")
        except compat.LoadError as error:
            if expect not in str(error):
                failures.append(f"strict_load {label}: unexpected message {error}")
    for label, doc, expect in [
        ("float version", compat.strict_load(b'{"version": 14.0, "categories": [], "templates": []}'), "decimal"),
        ("unknown key", {**_doc(1), "extra": 1}, "unknown key"),
        ("unknown kind", _doc(1, [_template(variables=[_var("PORT", "8080", kind="colour")])]), "kind"),
        ("unlisted category", _doc(1, [_template(category="Other")]), "not in the top-level categories"),
        ("featured unknown id", {**_doc(1), "featured": ["nope"]}, "neither a hosted"),
        ("null optional", _doc(1, [_template(variables=[_var("PORT", "8080", help=None)])]), "is null"),
        ("version 0", _doc(0), "at least 1"),
    ]:
        found = compat.schema_problems(doc)
        if not any(expect in p for p in found):
            failures.append(f"schema {label}: expected {expect!r}, got {found}")
    if compat.schema_problems(_doc(1)):
        failures.append(f"schema: the base document fails: {compat.schema_problems(_doc(1))}")

    # 3. The app's sanity rules (mirror of TemplateSanity, R10 cases included).
    for label, template, expect in SANITY_CASES:
        found = sanity.problems(template)
        if expect is None and found:
            failures.append(f"sanity {label}: expected clean, got {found}")
        elif expect is not None and not any(expect in p for p in found):
            failures.append(f"sanity {label}: expected {expect!r}, got {found}")
    for label, template, expect in TEXT_CASES:
        found = sanity.catalogue_rules(template)
        if expect is None and found:
            failures.append(f"text {label}: expected clean, got {found}")
        elif expect is not None and not any(expect in p for p in found):
            failures.append(f"text {label}: expected {expect!r}, got {found}")
    print(f"sanity: {len(SANITY_CASES)} cases, text: {len(TEXT_CASES)} cases")

    # 4. The version gate.
    base = _doc(13)
    bumped_template = _template(version=2, tagline="Changed")
    cases = [
        ("unchanged", base, base, None, None),
        ("plus one", base, _doc(14), None, None),
        ("plus two", base, _doc(15), None, "exactly the deployed version + 1"),
        ("same version other bytes", base, _doc(13, [_template(tagline="x")]), None, "still 13"),
        ("rollback", base, _doc(12), None, "exactly the deployed version + 1"),
        ("template changed, own version not bumped", base, _doc(14, [_template(tagline="Changed")]), None, "own version"),
        ("template changed and bumped", base, _doc(14, [bumped_template]), None, None),
        ("live above repo: alarm", base, _doc(14), _doc(15), "ALARM"),
        ("live same version other bytes", base, _doc(14), _doc(14, [_template(name="Other")]), "DIFFERENT version"),
        ("live behind (CDN) is fine", base, _doc(14), _doc(13), None),
    ]
    for label, deployed, current, live, expect in cases:
        gate = Gate("version")
        live_arg = None if live is None else (_raw(live), None)
        gate_version(gate, _raw(current), current, _raw(deployed), live_arg)
        if expect is None and gate.status == "FAIL":
            failures.append(f"version {label}: expected pass, got {gate.messages}")
        elif expect is not None and not any(expect in m for m in gate.messages):
            failures.append(f"version {label}: expected {expect!r}, got {gate.messages}")
    print(f"version: {len(cases)} cases")

    # 5. The risk helpers: the env file compose reads, the features read from its model, and the
    # escaping of template text in the summary the signer reads.
    env_text = risk.env_file_text({"TAG": "a$b c", "LD_PRELOAD": "/x.so", "DOCKER_HOST": "tcp://evil",
                                   "COMPOSE_FILE": "/etc/x.yml", "user": "u", "bad-key": "x"})
    if env_text != "TAG='a$b c'\nLD_PRELOAD='/x.so'\n":
        failures.append(f"risk env file: unexpected {env_text!r}")
    for value in ("it's", "a\nB=x", "a\rb"):
        try:
            risk.env_file_text({"K": value})
            failures.append(f"risk env file accepted {value!r}")
        except risk.ResolveError:
            pass
    for key in risk.HOST_FILE_KEYS:
        try:
            risk.resolve(_with_compose(f"services:\n  a:\n    image: x\n    {key}: /etc/passwd\n"), ("false",))
            failures.append(f"risk resolve ran compose on a template with {key}")
        except risk.ResolveError as error:
            if key not in str(error):
                failures.append(f"risk resolve {key}: {error}")
    model = {"services": {
        "a": {"use_api_socket": True, "build": {"context": "https://example.com/x.git", "ssh": ["default"],
                                                "secrets": [{"source": "s"}]}},
        "b": {"provider": {"type": "model"}},
        "c": {"build": {"context": "/p/stack"}},
        "d": {"volumes": [{"type": "bind", "source": "/p/stack/data", "target": "/data<!--"}]}}}
    found = risk.features(model, "/p/stack")
    for text, strong in [("a: use_api_socket (the container-engine socket, without a bind mount)", True),
                         ("a: builds an image on the host from https://example.com/x.git", True),
                         ("a: build ssh ['default'] (forwards the host's SSH agent or keys)", True),
                         ("a: build secret s", True),
                         ("b: provider model (runs a host-side plugin instead of a container)", True),
                         ("c: builds an image on the host from .", False)]:
        if (text, strong) not in found:
            failures.append(f"risk features: missing {(text, strong)} in {sorted(found)}")
    for raw, inert in [("/data<!--", "/data&lt;\\!\\-\\-"), ("**removed**: x", "\\*\\*removed\\*\\*: x"),
                       ("a\nb|c", "a b\\|c"), ("[x](http://e)", "\\[x\\]\\(http://e\\)")]:
        if md(raw) != inert:
            failures.append(f"summary escaping: md({raw!r}) = {md(raw)!r}, expected {inert!r}")
    print("risk helpers: env file, features, summary escaping")

    # 6. Signature checks with THROWAWAY keys (never the real ones).
    if shutil.which("minisign"):
        failures += _signature_self_test()
    else:
        print("signature: SKIPPED (minisign is not installed)")
        if os.environ.get("GITHUB_ACTIONS") == "true":
            failures.append("minisign is not installed in CI")

    if failures:
        print("\nSELF-TEST FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("\nself-test OK")
    return 0


def _signature_self_test():
    failures = []
    with tempfile.TemporaryDirectory(prefix="catalog-selftest-") as tmp:
        keys = os.path.join(tmp, "keys")
        os.mkdir(keys)

        def make(role, directory):
            subprocess.run(["minisign", "-G", "-W", "-p", os.path.join(directory, f"catalog-{role}.pub"),
                            "-s", os.path.join(directory, f"{role}.key")], check=True, capture_output=True)
        make("primary", keys)
        make("emergency", keys)
        other = os.path.join(tmp, "other")
        os.mkdir(other)
        make("primary", other)
        body = os.path.join(tmp, "templates.json")
        with open(body, "wb") as handle:
            handle.write(_raw(_doc(14)))

        def sign(key, comment, target=body):
            sig = target + ".minisig"
            subprocess.run(["minisign", "-S", "-s", key, "-m", target, "-x", sig, "-t", comment],
                           check=True, capture_output=True)
            with open(target, "rb") as b, open(sig, "rb") as s:
                return b.read(), s.read()

        primary, emergency = os.path.join(keys, "primary.key"), os.path.join(keys, "emergency.key")
        sha = "0123456789abcdef0123456789abcdef01234567"
        cases = [
            ("primary, plain comment", primary, "catalog=templates version=14", "any", None),
            ("primary, with commit", primary, f"catalog=templates version=14 commit={sha}", "any", None),
            ("emergency, as emergency", emergency, "catalog=templates version=14", "emergency", None),
            ("primary where emergency is required", primary, "catalog=templates version=14", "emergency", "expected the emergency"),
            ("wrong kind", primary, "catalog=channel version=14", "any", "is not 'catalog=templates"),
            ("version mismatch", primary, "catalog=templates version=13", "any", "version 13"),
            ("trailing junk", primary, "catalog=templates version=14 extra", "any", "is not 'catalog=templates"),
            ("leading zero", primary, "catalog=templates version=014", "any", "is not 'catalog=templates"),
            ("unknown key", os.path.join(other, "primary.key"), "catalog=templates version=14", "any", "not in keys/"),
        ]
        for label, key, comment, role, expect in cases:
            data, sig = sign(key, comment)
            try:
                signature.check_pair(data, sig, role, keys_dir=keys)
                if expect:
                    failures.append(f"signature {label}: accepted")
            except signature.PairError as error:
                if not expect or expect not in str(error):
                    failures.append(f"signature {label}: {error}")
        data, sig = sign(primary, "catalog=templates version=14")
        try:
            signature.check_pair(data.replace(b"Demo", b"Dem0"), sig, keys_dir=keys)
            failures.append("signature tampered body: accepted")
        except signature.PairError as error:
            if "does not verify" not in str(error):
                failures.append(f"signature tampered body: {error}")
        # A forged trusted comment (the global signature covers it).
        forged = sig.replace(b"version=14", b"version=15")
        try:
            signature.check_pair(_raw(_doc(15)), forged, keys_dir=keys)
            failures.append("signature forged comment: accepted")
        except signature.PairError:
            pass
        print(f"signature: {len(cases) + 2} cases (throwaway keys)")
    return failures


def main(argv=None):
    parser = argparse.ArgumentParser(description="The template catalogue gates.")
    parser.add_argument("--catalog", default=CATALOG)
    parser.add_argument("--deployed-ref", help="git ref of the deployed commit, or 'github' to ask the API")
    parser.add_argument("--live", action="store_true", help="also read the live templates.json")
    parser.add_argument("--live-url", default=LIVE_URL)
    parser.add_argument("--risk", action="store_true", help="resolve added and changed templates with compose")
    parser.add_argument("--compose", default="docker compose", help="the compose command for --risk")
    parser.add_argument("--summary", help="append the Markdown summary to this file")
    parser.add_argument("--no-banner", action="store_true",
                        help="leave the pipeline-change banner out (the workflow prints its own first)")
    parser.add_argument("--site", help="check a built site directory instead")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.site:
        problems = check_site(args.site)
        for problem in problems:
            print(f"FAIL  {problem}")
        if not problems:
            print("OK    the built site: templates.json byte-identical, no scripts, keys or helpers")
        return 1 if problems else 0
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
