"""Reading templates.json the way the apps do, and more strictly than they do.

Two layers:

* `meshdeck_v102_decodes(doc)` mirrors fielded meshDeck v1.0.2, whose `TemplateCatalogFile` is
  SYNTHESIZED Codable: one template the decoder cannot read fails the WHOLE file, so every
  meshDeck on a phone would show no hosted templates at all. The mirror is pinned by fixtures
  (scripts/fixtures/meshdeck-v1.0.2/, recorded by decoding each one with meshDeck's own model
  files at the tag; `check-catalog.py --self-test` must agree with every recorded answer).
  It is exact, not cautious: where the real decoder is lenient (an integral float version, an
  unknown key) so is the mirror, and the schema layer below is where we choose to be stricter.

* `strict_load(raw)` and `schema_problems(doc)` are the catalogue's own rules: UTF-8 without a
  BOM, no duplicate keys, integers written as integers, no lone surrogates, only the keys the
  shared model knows (new optional keys listed in ALLOWED_*), and `kind` from the shared enum.
"""
import json
import math

INT64_MIN, INT64_MAX = -(2 ** 63), 2 ** 63 - 1

# shared-1.4.0 TemplateVariable.Kind.
KINDS = {"text", "port", "number", "bool", "url", "path", "email", "timezone"}

ALLOWED_TOP = {"version", "categories", "templates", "featured"}
ALLOWED_TEMPLATE = {"id", "name", "tagline", "category", "symbol", "version", "compose", "variables", "notes",
                    "superStack"}
ALLOWED_VARIABLE = {"key", "label", "defaultValue", "isSecret", "help", "options", "isPreset", "credential",
                    "generate", "kind"}
ALLOWED_OPTION = {"text", "value"}
ALLOWED_CREDENTIAL = {"field", "group", "tier", "display"}
ALLOWED_GENERATE = {"charset"}

# The templates compiled into both apps (meshDeck v1.0.2 and meshDeckShared shared-1.4.0 hold the
# same 16). The hosted file overrides or adds by id, so `featured` may name one of these too.
SEED_IDS = {"wordpress", "nextcloud", "gitea", "vaultwarden", "uptime-kuma", "pihole", "home-assistant", "grafana",
            "jellyfin", "n8n", "media-automation", "observability", "nextcloud-suite", "download-station",
            "smart-home", "local-ai"}


# --- meshDeck v1.0.2 decode mirror ------------------------------------------------------

class _Reject(Exception):
    pass


def _string(value):
    if not isinstance(value, str):
        raise _Reject("not a string")
    # Foundation's JSONDecoder refuses a lone UTF-16 surrogate escape (recorded fixture).
    if any(0xD800 <= ord(ch) <= 0xDFFF for ch in value):
        raise _Reject("lone surrogate")
    return value


def _int(value):
    if isinstance(value, bool):
        raise _Reject("bool is not Int")
    if isinstance(value, int):
        if not INT64_MIN <= value <= INT64_MAX:
            raise _Reject("Int overflow")
        return value
    if isinstance(value, float):
        # JSONDecoder accepts 14.0 and 1.4e1 for an Int (recorded), not 14.5 or 1e30.
        if math.isfinite(value) and value.is_integer() and INT64_MIN <= value <= INT64_MAX:
            return int(value)
        raise _Reject("not an integral number")
    raise _Reject("not a number")


def _bool(value):
    if not isinstance(value, bool):
        raise _Reject("not a Bool")
    return value


def _required(obj, key, decode):
    if key not in obj or obj[key] is None:
        raise _Reject(f"missing {key}")
    return decode(obj[key])


def _optional(obj, key, decode):
    if key not in obj or obj[key] is None:
        return None
    return decode(obj[key])


def _object(value):
    if not isinstance(value, dict):
        raise _Reject("not an object")
    return value


def _array(decode):
    def inner(value):
        if not isinstance(value, list):
            raise _Reject("not an array")
        return [decode(item) for item in value]
    return inner


def _enum(cases):
    def inner(value):
        if _string(value) not in cases:
            raise _Reject(f"unknown enum value {value!r}")
        return value
    return inner


def _option(value):
    obj = _object(value)
    _required(obj, "text", _string)
    _required(obj, "value", _string)


def _credential(value):
    obj = _object(value)
    _required(obj, "field", _enum({"username", "password"}))
    _required(obj, "group", _string)
    _required(obj, "tier", _enum({"applied", "suggested"}))
    _required(obj, "display", _string)


def _generation(value):
    # Custom decoder: a keyed container; `charset` decodeIfPresent(String) mapped leniently.
    obj = _object(value)
    _optional(obj, "charset", _string)


def _variable(value):
    obj = _object(value)
    _required(obj, "key", _string)
    _required(obj, "label", _string)
    _required(obj, "defaultValue", _string)
    _required(obj, "isSecret", _bool)
    _optional(obj, "help", _string)
    _optional(obj, "options", _array(_option))
    _required(obj, "isPreset", _bool)
    _optional(obj, "credential", _credential)
    _optional(obj, "generate", _generation)


def _template(value):
    obj = _object(value)
    for key in ("id", "name", "tagline", "category", "symbol"):
        _required(obj, key, _string)
    _required(obj, "version", _int)
    _required(obj, "compose", _string)
    _required(obj, "variables", _array(_variable))
    _required(obj, "notes", _array(_string))
    _optional(obj, "superStack", _bool)


def meshdeck_v102_problem(doc):
    """None when meshDeck v1.0.2 decodes the whole file, else why not (first failure)."""
    try:
        obj = _object(doc)
        _required(obj, "version", _int)
        _required(obj, "categories", _array(_string))
        templates = obj.get("templates")
        if templates is None:
            raise _Reject("missing templates")
        if not isinstance(templates, list):
            raise _Reject("templates is not an array")
        for index, template in enumerate(templates):
            try:
                _template(template)
            except _Reject as error:
                tid = template.get("id") if isinstance(template, dict) else None
                raise _Reject(f"template {index} ({tid!r}): {error}") from None
        _optional(obj, "featured", _array(_string))
    except _Reject as error:
        return str(error)
    return None


def meshdeck_v102_decodes(doc):
    return meshdeck_v102_problem(doc) is None


def mirror_answer_for_text(text):
    """The mirror's answer for raw file text (what the fixtures record)."""
    try:
        doc = json.loads(text)
    except ValueError:
        return False
    return meshdeck_v102_decodes(doc)


# --- Strict loading ---------------------------------------------------------------------

class FloatLiteral(float):
    """A number written with a fraction or an exponent (kept apart so the schema can refuse it)."""


class LoadError(Exception):
    pass


def strict_load(raw):
    """Parse bytes as the catalogue must be written. Raises LoadError."""
    if raw.startswith(b"\xef\xbb\xbf"):
        raise LoadError("the file starts with a UTF-8 byte order mark")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise LoadError(f"not UTF-8: {error}") from None

    def pairs(items):
        seen = {}
        for key, value in items:
            if key in seen:
                raise LoadError(f"duplicate key {key!r} in one object")
            seen[key] = value
        return seen

    def constant(name):
        raise LoadError(f"{name} is not JSON")

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_float=FloatLiteral, parse_constant=constant)
    except LoadError:
        raise
    except ValueError as error:
        raise LoadError(f"not valid JSON: {error}") from None


def _walk_strings(node, path="$"):
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for key, value in node.items():
            yield f"{path}.{key}[key]", key
            yield from _walk_strings(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk_strings(value, f"{path}[{index}]")


def _walk_numbers(node, path="$"):
    if isinstance(node, bool):
        return
    if isinstance(node, (int, float)):
        yield path, node
    elif isinstance(node, dict):
        for key, value in node.items():
            yield from _walk_numbers(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk_numbers(value, f"{path}[{index}]")


def schema_problems(doc):
    """The catalogue's own shape rules, stricter than any decoder. A list of messages."""
    problems = []
    if not isinstance(doc, dict):
        return ["the top level is not an object"]
    for path, value in _walk_numbers(doc):
        if isinstance(value, FloatLiteral):
            problems.append(f"{path}: {value!r} is written as a decimal; numbers in the catalogue are integers")
    for path, value in _walk_strings(doc):
        if any(0xD800 <= ord(ch) <= 0xDFFF for ch in value):
            problems.append(f"{path}: contains a lone UTF-16 surrogate")

    def keys(obj, allowed, where):
        for key in obj:
            if key not in allowed:
                problems.append(f"{where}: unknown key {key!r} (add it to the allowed keys only with the apps' support)")

    def is_int(value, minimum):
        return isinstance(value, int) and not isinstance(value, bool) and minimum <= value <= INT64_MAX

    keys(doc, ALLOWED_TOP, "top level")
    if not is_int(doc.get("version"), 1):
        problems.append("version must be an integer of at least 1")
    categories = doc.get("categories")
    if not isinstance(categories, list) or not all(isinstance(c, str) and c.strip() for c in categories):
        problems.append("categories must be a list of non-empty strings")
        categories = []
    elif len(set(categories)) != len(categories):
        problems.append("categories lists a category twice")
    templates = doc.get("templates")
    if not isinstance(templates, list):
        return problems + ["templates must be a list"]
    ids = []
    for index, template in enumerate(templates):
        where = f"template {index}"
        if not isinstance(template, dict):
            problems.append(f"{where}: not an object")
            continue
        tid = template.get("id")
        if isinstance(tid, str):
            where = f"template {tid!r}"
            ids.append(tid)
        keys(template, ALLOWED_TEMPLATE, where)
        for key in ("id", "name", "tagline", "category", "symbol", "compose"):
            if not isinstance(template.get(key), str):
                problems.append(f"{where}: {key} must be a string")
        if not is_int(template.get("version"), 1):
            problems.append(f"{where}: version must be an integer of at least 1")
        if "superStack" in template and not isinstance(template["superStack"], bool):
            problems.append(f"{where}: superStack must be true or false (or absent)")
        notes = template.get("notes")
        if not isinstance(notes, list) or not all(isinstance(n, str) for n in notes):
            problems.append(f"{where}: notes must be a list of strings")
        if isinstance(template.get("category"), str) and template["category"] not in categories:
            problems.append(f"{where}: category {template['category']!r} is not in the top-level categories list")
        variables = template.get("variables")
        if not isinstance(variables, list):
            problems.append(f"{where}: variables must be a list")
            continue
        for vindex, variable in enumerate(variables):
            vwhere = f"{where} variable {vindex}"
            if not isinstance(variable, dict):
                problems.append(f"{vwhere}: not an object")
                continue
            if isinstance(variable.get("key"), str):
                vwhere = f"{where} variable {variable['key']}"
            keys(variable, ALLOWED_VARIABLE, vwhere)
            for key in ("key", "label", "defaultValue"):
                if not isinstance(variable.get(key), str):
                    problems.append(f"{vwhere}: {key} must be a string")
            for key in ("isSecret", "isPreset"):
                if not isinstance(variable.get(key), bool):
                    problems.append(f"{vwhere}: {key} must be true or false")
            for key, value in variable.items():
                if value is None:
                    problems.append(f"{vwhere}: {key} is null; leave an absent value out instead")
            if "help" in variable and not isinstance(variable["help"], str):
                problems.append(f"{vwhere}: help must be a string")
            if "kind" in variable and variable["kind"] not in KINDS:
                problems.append(f"{vwhere}: kind {variable['kind']!r} is not one of {sorted(KINDS)}")
            if "options" in variable:
                options = variable["options"]
                if not isinstance(options, list) or not options:
                    problems.append(f"{vwhere}: options must be a non-empty list")
                else:
                    for option in options:
                        if not isinstance(option, dict) or set(option) != ALLOWED_OPTION \
                                or not all(isinstance(option[k], str) for k in ALLOWED_OPTION):
                            problems.append(f"{vwhere}: each option is exactly {{text, value}}, both strings")
                    values = [o.get("value") for o in options if isinstance(o, dict)]
                    if len(set(map(str, values))) != len(values):
                        problems.append(f"{vwhere}: two options share a value")
                    if variable.get("defaultValue") not in values:
                        problems.append(f"{vwhere}: the default is not one of the options")
            if "credential" in variable:
                credential = variable["credential"]
                if not isinstance(credential, dict) or set(credential) != ALLOWED_CREDENTIAL \
                        or credential.get("field") not in ("username", "password") \
                        or credential.get("tier") not in ("applied", "suggested") \
                        or not all(isinstance(credential.get(k), str) for k in ("group", "display")):
                    problems.append(f"{vwhere}: credential must be {{field: username|password, group, "
                                    f"tier: applied|suggested, display}}")
            if "generate" in variable:
                generate = variable["generate"]
                if not isinstance(generate, dict) or not set(generate) <= ALLOWED_GENERATE \
                        or generate.get("charset", "standard") not in ("standard", "alphanumeric"):
                    problems.append(f"{vwhere}: generate must be {{}} or {{charset: standard|alphanumeric}}")
    if len(set(ids)) != len(ids):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        problems.append(f"template ids used twice: {', '.join(dupes)}")
    if "featured" in doc:
        featured = doc["featured"]
        if not isinstance(featured, list) or not all(isinstance(f, str) for f in featured):
            problems.append("featured must be a list of template ids")
        else:
            for fid in featured:
                if fid not in ids and fid not in SEED_IDS:
                    problems.append(f"featured names {fid!r}, which is neither a hosted nor a built-in template")
            if len(set(featured)) != len(featured):
                problems.append("featured lists a template twice")
    return problems
