#!/usr/bin/env python3
"""Deploy every template in templates.json on the local Docker daemon, confirm
its containers come up running, and tear them down. Exits non-zero if any fail —
so a template with a bad image (e.g. a repo that no longer exists) or invalid
compose is caught in CI before it reaches the app."""
import json, os, subprocess, sys, tempfile, time

CATALOG = os.path.join(os.path.dirname(__file__), "..", "templates.json")
PORT = [39000]

def value_for(v):
    if "PORT" in v["key"]:
        PORT[0] += 1
        return str(PORT[0])
    return "Testpass123!" if v["isSecret"] else (v["defaultValue"] or "test")

def run(args, env, timeout):
    return subprocess.run(args, env=env, capture_output=True, text=True, timeout=timeout)

def default_port_collisions(t):
    """Two port vars sharing a default host port would clash on a default deploy — but CI
    assigns unique ports, so it wouldn't otherwise be caught. Return {port: [keys]} for clashes."""
    seen = {}
    for v in t["variables"]:
        if "PORT" in v["key"] and v.get("defaultValue"):
            seen.setdefault(v["defaultValue"], []).append(v["key"])
    return {p: ks for p, ks in seen.items() if len(ks) > 1}

def validate(t):
    """A super stack (e.g. a VPN killswitch) can't fully deploy in CI — its download client has
    no network until the VPN connects with real credentials, and it pulls ~10 heavy images. So
    validate the compose parses and interpolates (NOT a runtime guarantee); the owner verifies
    the VPN path live."""
    env = dict(os.environ)
    for v in t["variables"]:
        env[v["key"]] = value_for(v)
    with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
        f.write(t["compose"]); path = f.name
    try:
        res = run(["docker", "compose", "-f", path, "config", "-q"], env, 60)
        if res.returncode != 0:
            return False, (res.stderr.strip().splitlines() or [""])[-1][:200]
        return True, "config valid (super stack — not deployed in CI)"
    except subprocess.TimeoutExpired:
        return False, "config timed out"
    finally:
        os.unlink(path)

def test(t):
    proj = "mdtest-" + t["id"]
    env = dict(os.environ)
    for v in t["variables"]:
        env[v["key"]] = value_for(v)
    with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
        f.write(t["compose"]); path = f.name
    base = ["docker", "compose", "-p", proj, "-f", path]
    try:
        up = run(base + ["up", "-d"], env, 240)
        if up.returncode != 0:
            return False, (up.stderr.strip().splitlines() or [""])[-1][:200]
        # Poll up to 60s: a multi-service app waits on its DB's healthcheck.
        states, bad = [], []
        for _ in range(12):
            time.sleep(5)
            ps = run(base + ["ps", "--format", "json"], env, 30)
            states = [json.loads(l) for l in ps.stdout.strip().splitlines() if l.strip()]
            bad = [s for s in states if s.get("State") != "running" or "Restarting" in (s.get("Status") or "")]
            if states and not bad:
                return True, ", ".join(s.get("Service") for s in states)
        if not states:
            return False, "no containers started"
        return False, ", ".join(f"{s.get('Service')}={s.get('State')}" for s in bad)
    except subprocess.TimeoutExpired:
        return False, "timed out"
    finally:
        run(base + ["down", "-v", "--remove-orphans"], env, 120)
        os.unlink(path)

# Super stacks that can't fully deploy in CI: a real VPN credential (killswitch) gates startup
# (media-stack, media-stack-wg), or the stack is too heavy for a shared runner (immich: ~3 GB of
# images + a first-boot DB migration; localai: ~5 GB of images + a first-boot model download).
# These are config-validated, not deployed; the owner verifies them live. Every other super stack
# (e.g. observability, smart-home) deploys fully.
VALIDATE_ONLY = {"media-stack", "media-stack-wg", "immich", "localai"}

def main():
    cat = json.load(open(CATALOG))
    failures = []
    for t in cat["templates"]:
        clashes = default_port_collisions(t)
        if clashes:
            print(f"FAIL  {t['id']:16} default port collision: {clashes}", flush=True)
            failures.append(t["id"])
            continue
        ok, detail = validate(t) if t["id"] in VALIDATE_ONLY else test(t)
        print(f"{'OK  ' if ok else 'FAIL'}  {t['id']:16} {detail}", flush=True)
        if not ok:
            failures.append(t["id"])
    total = len(cat["templates"])
    print(f"\n{total - len(failures)}/{total} templates OK")
    if failures:
        print("FAILED:", ", ".join(failures))
        sys.exit(1)

if __name__ == "__main__":
    main()
