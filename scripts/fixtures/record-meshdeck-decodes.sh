#!/usr/bin/env bash
# Records what fielded meshDeck v1.0.2 does with each compatibility fixture: it decodes
# scripts/fixtures/meshdeck-v1.0.2/*.json with meshDeck's OWN model files (git show of
# the tag, nothing edited) and JSONDecoder, in one swift:6.3 container, and writes
# expected.json (fixture name -> true when the whole file decodes).
#
#   scripts/fixtures/record-meshdeck-decodes.sh /path/to/meshDeck [tag]
#
# check-catalog.py --self-test then requires its Python mirror of that decoder to agree
# with every recorded answer, so the mirror cannot drift from the real app. Re-run this
# when fixtures are added, or against a newer meshDeck tag (new directory, new mirror).
#
# Needs Docker. One container, removed when it exits; no network inside it.
set -euo pipefail

MESHDECK="${1:?usage: record-meshdeck-decodes.sh /path/to/meshDeck [tag]}"
TAG="${2:-v1.0.2}"
HERE="$(cd "$(dirname "$0")" && pwd)"
FIXTURES="$HERE/meshdeck-$TAG"
IMAGE="${SWIFT_IMAGE:-swift:6.3}"
MODELS="Packages/MeshDeckCore/Sources/MeshDeckModels/Templates"

[ -d "$FIXTURES" ] || { echo "no fixtures at $FIXTURES" >&2; exit 2; }
git -C "$MESHDECK" rev-parse --verify --quiet "$TAG^{commit}" >/dev/null || { echo "$MESHDECK has no tag $TAG" >&2; exit 2; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/src"
for f in TemplateCatalogFile StackTemplate TemplateVariable; do
  git -C "$MESHDECK" show "$TAG:$MODELS/$f.swift" > "$WORK/src/$f.swift"
done

# The model files mention two types from elsewhere in MeshDeckModels, only in code that is
# not part of decoding (envEntries). Minimal stand-ins so the three files compile alone.
cat > "$WORK/src/Stubs.swift" <<'SWIFT'
public struct SecretRef: Sendable, Hashable, Codable {}
public struct EnvEntry: Sendable, Hashable {
    public enum Value: Sendable, Hashable { case plain(String), secret(SecretRef) }
    public let key: String
    public let value: Value
    public init(key: String, value: Value) { self.key = key; self.value = value }
}
SWIFT

# Exactly meshDeck's call (TemplateCatalogModel.swift: JSONDecoder().decode(TemplateCatalogFile.self, from:)).
cat > "$WORK/src/main.swift" <<'SWIFT'
import Foundation
for path in CommandLine.arguments.dropFirst() {
    let name = URL(fileURLWithPath: path).lastPathComponent
    do {
        let data = try Data(contentsOf: URL(fileURLWithPath: path))
        _ = try JSONDecoder().decode(TemplateCatalogFile.self, from: data)
        print("ACCEPT \(name)")
    } catch {
        print("REJECT \(name)")
    }
}
SWIFT

docker run --rm --network none \
  -v "$WORK/src:/src:ro" -v "$FIXTURES:/fixtures:ro" "$IMAGE" \
  bash -c 'swiftc -swift-version 5 -O /src/*.swift -o /tmp/decode && /tmp/decode /fixtures/*.json' \
  > "$WORK/out.txt"

python3 - "$WORK/out.txt" "$FIXTURES/expected.json" "$TAG" "$(git -C "$MESHDECK" rev-parse "$TAG^{commit}")" "$IMAGE" <<'PY'
import json, sys
out, dest, tag, commit, image = sys.argv[1:]
answers = {}
for line in open(out):
    verdict, name = line.split()
    if name == "expected.json":
        continue
    answers[name] = verdict == "ACCEPT"
doc = {"meshDeck": tag, "commit": commit, "image": image, "decodes": dict(sorted(answers.items()))}
with open(dest, "w") as handle:
    json.dump(doc, handle, indent=2)
    handle.write("\n")
print(f"{len(answers)} fixtures: {sum(answers.values())} decode, {len(answers) - sum(answers.values())} rejected")
PY
