#!/usr/bin/env python3
"""Prove meshDeck's own templates run on the OLDEST Compose we promise to support.

The floor is **Compose 2.26.1** — the version Debian 13 stable ships from its own repos.
Ubuntu 24.04/26.04 ship 2.40, Fedora ships 5.5; Debian 12 ships 1.29.2 and needs Docker's
repository. The binding feature is `configs:` with inline `content:`, used by three
templates: Compose 2.23 rejects it outright and 2.24 is the first that really mounts it.

Why this does a real deploy rather than a validation:

  * `config -q` passes on 2.0.1 and 2.23.0, both of which fail for real.
  * `up --dry-run` FAILS on `configs.content` at the floor (dry-run never materialises the
    inline config), so it would red-fail the very templates it exists to protect — and it
    mounts nothing either, so it could not detect a provider that accepts the file and
    silently skips the mount.

Only starting the container and reading the file back proves it. Everything else gets the
cheap syntax sweep.
"""
import json, os, re, subprocess, sys, tempfile

CATALOG = os.path.join(os.path.dirname(__file__), "..", "templates.json")
COMPOSE = os.environ.get("COMPOSE_BIN", "docker-compose-floor")
PORT = [41000]


def value_for(v):
    if "PORT" in v["key"]:
        PORT[0] += 1
        return str(PORT[0])
    return "Testpass123!" if v["isSecret"] else (v["defaultValue"] or "test")


def env_for(t):
    env = dict(os.environ)
    for v in t.get("variables", []):
        env[v["key"]] = value_for(v)
    return env


def compose(args, env, timeout=600):
    return subprocess.run([COMPOSE] + args, env=env, capture_output=True, text=True, timeout=timeout)


def templates():
    with open(CATALOG) as handle:
        catalog = json.load(handle)
    found, seen = [], set()

    def walk(node):
        if isinstance(node, dict):
            text = node.get("compose")
            if isinstance(text, str) and "\n" in text and node.get("id") not in seen:
                seen.add(node.get("id"))
                found.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(catalog)
    return found


def inline_config_targets(text):
    """`{service: [target, …]}` for services mounting a config declared with inline
    `content:`. A text scan, not a parse — the catalog is hand-written and regular, and this
    avoids a YAML dependency for the one shape that matters."""
    if not re.search(r"^configs:", text, re.M):
        return {}
    if not re.search(r"^\s+content:", text, re.M):
        return {}
    targets, service = {}, None
    for line in text.splitlines():
        service_match = re.match(r"^  (\w[\w.-]*):\s*$", line)
        if service_match:
            service = service_match.group(1)
        target_match = re.match(r"^\s+target:\s*(\S+)", line)
        if target_match and service:
            targets.setdefault(service, []).append(target_match.group(1).strip('"\''))
    return targets


def check_floor(t):
    """Deploy for real at the floor and read each mounted config back out."""
    targets = inline_config_targets(t["compose"])
    project = "mdfloor-" + t["id"]
    env = env_for(t)
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "compose.yaml")
        with open(path, "w") as handle:
            handle.write(t["compose"])
        base = ["-p", project, "-f", path, "--project-directory", directory]
        try:
            up = compose(base + ["up", "-d", "--wait-timeout", "120"], env)
            if up.returncode != 0:
                return False, "up failed: " + (up.stderr.strip().splitlines() or [""])[-1][:300]
            for service, paths in targets.items():
                for target in paths:
                    read = compose(base + ["exec", "-T", service, "cat", target], env, timeout=120)
                    if read.returncode != 0 or not read.stdout.strip():
                        return False, f"{service}:{target} was not mounted at the floor"
            return True, f"mounted {sum(len(v) for v in targets.values())} config(s)"
        except subprocess.TimeoutExpired:
            return False, "timed out"
        finally:
            compose(base + ["down", "-v", "--remove-orphans"], env, timeout=300)


def sweep(t):
    env = env_for(t)
    with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as handle:
        handle.write(t["compose"])
        path = handle.name
    try:
        res = compose(["-f", path, "config", "-q"], env, timeout=90)
        if res.returncode != 0:
            return False, (res.stderr.strip().splitlines() or [""])[-1][:200]
        return True, "parses"
    finally:
        os.unlink(path)


def main():
    version = subprocess.run([COMPOSE, "version", "--short"], capture_output=True, text=True)
    print(f"floor compose: {version.stdout.strip()}\n")
    all_templates = templates()
    deep = [t for t in all_templates if inline_config_targets(t["compose"])]
    print(f"{len(all_templates)} templates; {len(deep)} use configs.content and get a real deploy\n")
    failures = []

    for t in all_templates:
        ok, detail = sweep(t)
        if not ok:
            failures.append((t["id"], "sweep", detail))
            print(f"FAIL  {t['id']}: {detail}")
    print()
    for t in deep:
        ok, detail = check_floor(t)
        print(f"{'ok  ' if ok else 'FAIL'}  {t['id']}: {detail}")
        if not ok:
            failures.append((t["id"], "floor", detail))

    if failures:
        print(f"\n{len(failures)} failure(s) at the floor. A template that needs a newer "
              f"Compose than {version.stdout.strip()} raises meshDeck's minimum — that is a "
              f"deliberate decision, not something to land silently. See "
              f"docs/COMPOSE_PROVIDER_PLAN.md in the app repo.")
        return 1
    print("\nEvery template runs on the oldest Compose we promise to support.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
