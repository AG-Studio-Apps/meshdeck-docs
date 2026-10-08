#!/usr/bin/env bash
# Differential test of scripts/catalog_sanity.py against meshTerm's REAL TemplateSanity: compiles
# meshTerm's TemplateSanity.swift and ComposeKeyLines.swift with meshDeckShared's model and
# validation files (read with cat / git show, nothing edited) in one swift:6.3 container, runs
# both over the deployed catalogue, this catalogue and every check-catalog.py self-test case,
# and requires the same verdict (shown or hidden), refusals (line:key), undeclared placeholders
# and reserved keys for every template.
#
#   scripts/fixtures/compare-meshterm-sanity.sh /path/to/meshTerm /path/to/meshDeckShared [tag] [deployed-ref]
#
# Run it whenever meshTerm's TemplateSanity changes. Needs Docker; no network inside it.
set -euo pipefail

MESHTERM="${1:?usage: compare-meshterm-sanity.sh /path/to/meshTerm /path/to/meshDeckShared [tag] [deployed-ref]}"
SHARED="${2:?usage: compare-meshterm-sanity.sh /path/to/meshTerm /path/to/meshDeckShared [tag] [deployed-ref]}"
TAG="${3:-shared-1.4.0}"
DEPLOYED="${4:-origin/main}"
IMAGE="${SWIFT_IMAGE:-swift:6.3}"
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS="$(cd "$HERE/.." && pwd)"
ENGINE="$MESHTERM/Packages/MeshTermContainerEngine/Sources/MeshTermContainerEngine/Templates"

[ -f "$ENGINE/TemplateSanity.swift" ] || { echo "no TemplateSanity.swift under $ENGINE" >&2; exit 2; }
git -C "$SHARED" rev-parse --verify --quiet "$TAG^{commit}" >/dev/null || { echo "$SHARED has no tag $TAG" >&2; exit 2; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/src" "$WORK/in"
for f in StackTemplate TemplateVariable StackTemplate+Validation; do
  git -C "$SHARED" show "$TAG:Sources/MeshDeckModels/Templates/$f.swift" > "$WORK/src/$f.swift"
done
git -C "$SHARED" show "$TAG:Sources/MeshDeckModels/Stacks/StackName.swift" > "$WORK/src/StackName.swift"
# The merge helper at the end of the validation file needs the compiled seed; validate() and
# validateStrict() come before it.
python3 - "$WORK/src/StackTemplate+Validation.swift" <<'PY'
import sys
path = sys.argv[1]
text = open(path).read()
cut = text.find("/// The gallery's catalogue: the bundled seed")
open(path, "w").write(text if cut < 0 else text[:cut])
PY
grep -v '^import MeshDeckModels' "$ENGINE/TemplateSanity.swift" > "$WORK/src/TemplateSanity.swift"
cp "$ENGINE/ComposeKeyLines.swift" "$WORK/src/"
cat > "$WORK/src/Stubs.swift" <<'SWIFT'
public struct SecretRef: Sendable, Hashable, Codable {}
public struct EnvEntry: Sendable, Hashable {
    public enum Value: Sendable, Hashable { case plain(String), secret(SecretRef) }
    public let key: String
    public let value: Value
    public init(key: String, value: Value) { self.key = key; self.value = value }
}
SWIFT
cat > "$WORK/src/main.swift" <<'SWIFT'
import Foundation
for path in CommandLine.arguments.dropFirst() {
    let templates = try! JSONDecoder().decode([StackTemplate].self, from: Data(contentsOf: URL(fileURLWithPath: path)))
    for (index, template) in templates.enumerated() {
        let problems = TemplateSanity.problems(template)
        var refused: [String] = [], undeclared: Set<String> = [], reserved: Set<String> = []
        for problem in problems {
            switch problem {
            case .refusedCompose(let line, let key): refused.append("\(line):\(key)")
            case .undeclaredPlaceholder(let name): undeclared.insert(name)
            case .reservedKey(let key): reserved.insert(key)
            default: break
            }
        }
        let name = URL(fileURLWithPath: path).lastPathComponent
        print("\(name)#\(index)\t\(problems.isEmpty ? "shown" : "hidden")\t\(refused.sorted().joined(separator: ","))\t\(undeclared.sorted().joined(separator: ","))\t\(reserved.sorted().joined(separator: ","))")
    }
}
SWIFT

cd "$SCRIPTS"
python3 - "$WORK/in" "$DEPLOYED" > "$WORK/python.tsv" <<'PY'
import importlib.util, json, subprocess, sys
import catalog_sanity as sanity
out, deployed = sys.argv[1:]
spec = importlib.util.spec_from_file_location("check_catalog", "check-catalog.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)
inputs = {
    "cases.json": [t for _, t, _ in check.SANITY_CASES],
    "current.json": json.load(open("../templates.json"))["templates"],
    "deployed.json": json.loads(subprocess.run(["git", "show", f"{deployed}:templates.json"], check=True,
                                               capture_output=True, text=True).stdout)["templates"],
}
for name, templates in inputs.items():
    json.dump(templates, open(f"{out}/{name}", "w"))
    for index, t in enumerate(templates):
        refused = sorted(f"{line}:{key}" for line, key in sanity.refusals(t["compose"]))
        declared = {v["key"] for v in t["variables"]}
        texts = [t["compose"]] + [v["defaultValue"] for v in t["variables"]] \
            + [o["value"] for v in t["variables"] for o in v.get("options") or []]
        undeclared = sorted({n for x in texts for n in sanity.placeholder_names(x)} - declared)
        reserved = sorted({v["key"] for v in t["variables"] if sanity.is_reserved_key(v["key"])})
        verdict = "hidden" if sanity.problems(t) else "shown"
        print(f"{name}#{index}\t{verdict}\t{','.join(refused)}\t{','.join(undeclared)}\t{','.join(reserved)}")
PY

docker run --rm --network none -v "$WORK/src:/src:ro" -v "$WORK/in:/in:ro" "$IMAGE" \
  bash -c 'swiftc -swift-version 6 -O /src/*.swift -o /tmp/sanity && /tmp/sanity /in/cases.json /in/current.json /in/deployed.json' \
  > "$WORK/swift.tsv"

if diff <(sort "$WORK/swift.tsv") <(sort "$WORK/python.tsv"); then
  echo "IDENTICAL: $(wc -l < "$WORK/python.tsv") templates; catalog_sanity.py agrees with meshTerm's TemplateSanity."
else
  echo "DIFFERENT: the lines above are where catalog_sanity.py (>) and TemplateSanity (<) disagree." >&2
  exit 1
fi
