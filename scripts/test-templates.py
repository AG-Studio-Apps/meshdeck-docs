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
        time.sleep(18)
        ps = run(base + ["ps", "--format", "json"], env, 30)
        states = [json.loads(l) for l in ps.stdout.strip().splitlines() if l.strip()]
        if not states:
            return False, "no containers started"
        bad = [s for s in states if s.get("State") != "running" or "Restarting" in (s.get("Status") or "")]
        if bad:
            return False, ", ".join(f"{s.get('Service')}={s.get('State')}" for s in bad)
        return True, ", ".join(s.get("Service") for s in states)
    except subprocess.TimeoutExpired:
        return False, "timed out"
    finally:
        run(base + ["down", "-v", "--remove-orphans"], env, 120)
        os.unlink(path)

def main():
    cat = json.load(open(CATALOG))
    failures = []
    for t in cat["templates"]:
        ok, detail = test(t)
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
