"""The template rules the apps enforce, mirrored so CI fails before a phone hides a template.

Ported line for line from meshTerm's `TemplateSanity.swift` and `ComposeKeyLines.swift`
(MeshTermContainerEngine, S4a plus the R10 fixes and the shared-1.4.0 repin) and from
meshDeckShared shared-1.4.0's `StackTemplate.validate()` / `validateStrict()`
(`StackTemplate+Validation.swift`) and `StackName.isValid`. Where the Swift reads a string by
`Character` (grapheme cluster) this reads code points, which only ever makes a length cap
STRICTER here (a flag emoji is one Character but two code points), never looser.

`problems(template)` returns what meshTerm's TemplateSanity would find (a template with any is
hidden on the phone). `catalogue_rules(template)` adds the CI-only rules of plan 4.3 items 4
and 7: brand-neutral text, no em-dash or en-dash in display text, no published secret default.
"""
import re
import unicodedata

# --- Caps (TemplateSanity) ---------------------------------------------------------------
NAME_LIMIT = 60
TAGLINE_LIMIT = 140
CATEGORY_LIMIT = 40
SYMBOL_LIMIT = 64
NOTE_LIMIT = 800
NOTE_COUNT = 12
HELP_LIMIT = 300
LABEL_LIMIT = 80
DEFAULT_LIMIT = 512
VARIABLE_COUNT = 64
COMPOSE_BYTES = 256 * 1024

# Upstream StackTemplate.sessionVariableNames (shared-1.4.0, with the S4-U review's additions)
# united with meshTerm's list. Compared UPPER-CASED (meshTerm's rule, stricter than upstream).
SESSION_KEYS = {
    "USER", "LOGNAME", "HOME", "PATH", "SHELL", "PWD", "OLDPWD", "MAIL", "TERM", "LANG", "LANGUAGE", "SHLVL",
    "SSH_AUTH_SOCK", "SSH_CLIENT", "SSH_CONNECTION", "SSH_TTY", "SSH_ORIGINAL_COMMAND", "SSH_AGENT_PID",
    "DISPLAY", "MOTD_SHOWN", "TMPDIR", "HOSTNAME",
    "DBUS_SESSION_BUS_ADDRESS", "_", "SSH_ASKPASS", "SSH_USER_AUTH", "SSH_AUTH_INFO_0", "KRB5CCNAME",
    "CONTAINER_HOST", "CONTAINER_CONNECTION", "CONTAINER_SSHKEY", "CONTAINER_PASSPHRASE",
}
RESERVED_PREFIXES = ["XDG_", "LC_", "COMPOSE_", "DOCKER_", "BUILDKIT_", "PODMAN_", "CONTAINERS_", "NERDCTL_",
                     "CONTAINERD_"]
# ALM, LRM, RLM, LRE, RLE, PDF, LRO, RLO, LRI, RLI, FSI, PDI (R10).
BIDI_CONTROLS = {0x061C, 0x200E, 0x200F, 0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069}

# TemplateVariable.looksSecret.
SECRET_WORDS = ["PASSWORD", "PASSWD", "PASSPHRASE", "SECRET", "TOKEN", "API_KEY", "APIKEY", "PRIVATE_KEY"]

BRAND = re.compile(r"mesh\s?(?:deck|term)(?![a-z])", re.IGNORECASE)
DASHES = {"\u2014": "em-dash", "\u2013": "en-dash"}


# --- Upstream validate() (shared-1.4.0) ----------------------------------------------------

def _swift_is_letter_or_number(ch):
    return unicodedata.category(ch)[0] in ("L", "N")


def stack_name_is_valid(name):
    """StackName.isValid: lowercase ASCII letters, digits, - and _, starting with a letter or digit."""
    if not name or not _swift_is_letter_or_number(name[0]):
        return False
    if not name.isascii():
        return False
    return all((c.isalpha() and c.islower()) or c.isdigit() or c in "-_" for c in name)


def is_env_name(key):
    if not key:
        return False
    first = key[0]
    if not (first == "_" or (first.isascii() and first.isalpha())):
        return False
    return all(c == "_" or (c.isascii() and (c.isalpha() or c.isdigit())) for c in key)


def placeholder_uses(compose):
    """StackTemplate.placeholderUses: braced uses outside `$$`, with whether each has a default."""
    uses = []
    position = 0
    while True:
        start = compose.find("${", position)
        if start < 0:
            break
        dollars = 0
        cursor = start
        while cursor > 0 and compose[cursor - 1] == "$":
            dollars += 1
            cursor -= 1
        after = start + 2
        if dollars % 2 == 1:
            position = after
            continue
        end = compose.find("}", after)
        if end < 0:
            break
        inner = compose[after:end]
        name = ""
        for ch in inner:
            if _swift_is_letter_or_number(ch) or ch == "_":
                name += ch
            else:
                break
        modifier = inner[len(name):]
        if name:
            uses.append((name, modifier.startswith(":-") or modifier.startswith("-")))
        position = end + 1
    return uses


def validate(template):
    """StackTemplate.validate(): a list of issue strings."""
    issues = []
    if not stack_name_is_valid(template["id"]):
        issues.append(f"id {template['id']!r} is not a valid stack name")
    if not template["name"].strip(_WS):
        issues.append("empty name")
    if not template["category"].strip(_WS):
        issues.append("empty category")
    if not template["compose"].strip():
        issues.append("empty compose")
    keys = set()
    for variable in template["variables"]:
        if not is_env_name(variable["key"]):
            issues.append(f"variable key {variable['key']!r} is not an env name")
        if variable["key"] in keys:
            issues.append(f"variable {variable['key']} is declared twice")
        keys.add(variable["key"])
    reported = set()
    for name, has_default in placeholder_uses(template["compose"]):
        if not has_default and name not in keys and name not in reported:
            reported.add(name)
            issues.append(f"${{{name}}} is used but not declared")
    return issues


# --- ComposeKeyLines ---------------------------------------------------------------------

class Line:
    __slots__ = ("number", "indent", "key", "value", "is_list_item", "path")

    def __init__(self, number, indent, key, value, is_list_item, path):
        self.number, self.indent, self.key, self.value = number, indent, key, value
        self.is_list_item, self.path = is_list_item, path


# Swift CharacterSet.whitespaces: tab and the Unicode space separators (Zs).
_WS = "\t" + "".join(chr(c) for c in range(0x3001) if unicodedata.category(chr(c)) == "Zs")


def strip_comment(value):
    quote = None
    previous = " "
    for index, ch in enumerate(value):
        if quote is not None:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and previous in (" ", "\t"):
            return value[:index].strip(_WS)
        previous = ch
    return value.strip(_WS)


def split_key(content):
    """ComposeKeyLines.split: (key or None, value) of one line's content after any list dash."""
    if not content:
        return None, ""
    first = content[0]
    if first in "{[":
        return None, strip_comment(content)
    if first in "\"'":
        index = 1
        while index < len(content):
            if content[index] == first:
                nxt = index + 1
                if first == "'" and nxt < len(content) and content[nxt] == "'":
                    index = nxt + 1
                    continue
                after_quote = content[nxt:].lstrip(" ")
                if after_quote.startswith(":"):
                    tail = after_quote[1:]
                    if not tail or tail[0] == " ":
                        return content[1:index], strip_comment(tail)
                return None, strip_comment(content)
            if first == '"' and content[index] == "\\":
                index = min(index + 2, len(content))
                continue
            index += 1
        return None, strip_comment(content)
    index = 0
    while index < len(content):
        if content[index] == ":":
            nxt = index + 1
            if nxt == len(content) or content[nxt] == " ":
                key = content[:index].strip(_WS)
                return (key or None), strip_comment(content[nxt:])
        if content[index] == " " and content[index + 1:].startswith("#"):
            break
        index += 1
    return None, strip_comment(content)


def starts_block_scalar(value):
    if not value or value[0] not in "|>":
        return False
    return all(c in "+-0123456789" for c in value[1:])


def compose_key_lines(text):
    out = []
    stack = []  # (indent, key)
    block_indent = None
    normalised = text.replace("\r\n", "\n")
    for index, raw in enumerate(normalised.split("\n")):
        content = raw.lstrip(" ")
        indent = len(raw) - len(content)
        if not content or content.isspace() or all(c.isspace() for c in content):
            continue
        if block_indent is not None:
            if indent > block_indent:
                continue
            block_indent = None
        if content.startswith("#") or content == "---" or content == "...":
            continue
        rest = content
        column = indent
        is_list_item = False
        if rest == "-" or rest.startswith("- "):
            is_list_item = True
            after_dash = rest[1:].lstrip(" ")
            column += len(rest) - len(after_dash)
            rest = after_dash
        key, value = split_key(rest)
        while stack and stack[-1][0] >= column:
            stack.pop()
        out.append(Line(index + 1, column, key, value, is_list_item, [k for _, k in stack]))
        if key is not None:
            stack.append((column, key))
        if starts_block_scalar(value):
            block_indent = indent if (key is None and is_list_item) else column
    return out


# --- TemplateSanity rules ---------------------------------------------------------------

def has_control_characters(value, allow_newline):
    for ch in value:
        if allow_newline and ch == "\n":
            continue
        if ord(ch) in BIDI_CONTROLS:
            return True
        if unicodedata.category(ch) in ("Cc", "Zl", "Zp"):
            return True
    return False


def is_reserved_key(key):
    upper = key.upper()
    return upper in SESSION_KEYS or any(upper.startswith(p) for p in RESERVED_PREFIXES)


def _is_name_start(ch):
    return ch == "_" or (ch.isascii() and ch.isalpha())


def _is_name_char(ch):
    return _is_name_start(ch) or ch in "0123456789"


def placeholder_names(text):
    """Every variable compose would interpolate: braced (nested too) and bare `$NAME`; `$$` escapes."""
    names = []
    index = 0
    n = len(text)

    def read_name(start):
        end = start
        while end < n and _is_name_char(text[end]):
            end += 1
        return text[start:end], end

    while index < n:
        if text[index] != "$":
            index += 1
            continue
        run = 0
        while index < n and text[index] == "$":
            run += 1
            index += 1
        if run % 2 != 1 or index >= n:
            continue
        if text[index] == "{":
            name, end = read_name(index + 1)
            if name:
                names.append(name)
            index = end
        elif _is_name_start(text[index]):
            name, end = read_name(index)
            names.append(name)
            index = end
    return names


def without_node_properties(value):
    rest = value
    while rest and rest[0] in "&!":
        space = rest.find(" ")
        rest = "" if space < 0 else rest[space:].lstrip(" ")
    return rest


def has_numeric_escape(line):
    previous = None
    for ch in line:
        if previous == "\\" and ch in "xuU":
            return True
        previous = None if (previous == "\\" and ch == "\\") else ch
    return False


def has_alias(value, flow):
    if value.startswith("*"):
        return True
    if not flow:
        return False
    previous = " "
    quote = None
    for ch in value:
        if quote is not None:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "*" and previous in "{[,: ":
            return True
        previous = ch
    return False


def _word_char(ch):
    return ch.isalpha() or ch.isnumeric() or ch in "_-"


def mentions_key(key, value):
    for form in (key, f'"{key}"', f"'{key}'"):
        start = 0
        while True:
            found = value.find(form, start)
            if found < 0:
                break
            before = " " if found == 0 else value[found - 1]
            after = value[found + len(form):].lstrip(" ")
            if after.startswith(":") and not _word_char(before):
                return True
            start = found + len(form)
    return False


def refusals(compose):
    """4.3 item 7's compose forms and the YAML forms (R10) that would carry them past a line reader.
    A list of (line, key)."""
    found = []
    guarded = {"volumes", "secrets", "configs"}
    normalised = compose.replace("\r\n", "\n")
    for index, raw in enumerate(normalised.split("\n")):
        if has_numeric_escape(raw):
            found.append((index + 1, "\\"))
    for line in compose_key_lines(compose):
        top = line.path[0] if line.path else (line.key or "")
        body = without_node_properties(line.value)
        flow = body.startswith("{") or body.startswith("[")
        alias = has_alias(line.value, flow)

        def refuse(key, line=line):
            found.append((line.number, key))

        head = line.key if line.key is not None else line.value
        if head == "?" or head.startswith("? "):
            refuse("?")
        if line.key is not None and line.key.startswith("!"):
            refuse("!")
        if not line.path and not line.is_list_item and (head.startswith("---") or head.startswith("...")
                                                         or head.startswith("%")):
            refuse("---")
        if not line.path and not line.is_list_item and line.key is None and flow:
            refuse("{")
        if not line.path and not line.is_list_item and line.key in ("include", "name", "<<"):
            refuse(line.key)
        if line.key == "file" and "extends" in line.path:
            refuse("extends")
        if "extends" in line.path and (line.key == "<<" or alias):
            refuse("extends")
        if line.key == "extends" and (alias or (flow and (mentions_key("file", line.value)
                                                          or mentions_key("<<", line.value)))):
            refuse("extends")
        if line.key != "extends" and flow and mentions_key("extends", line.value) and (
                alias or mentions_key("file", line.value) or mentions_key("<<", line.value)):
            refuse("extends")
        if top not in guarded or not ((line.path and line.path[0] == top) or not line.path):
            continue
        if line.key == "<<" or (flow and mentions_key("<<", line.value)):
            refuse("<<")
        elif alias:
            refuse("*")
        if top == "volumes":
            if line.key == "device" or (flow and mentions_key("device", line.value)):
                refuse("driver_opts")
        else:
            for key in ("file", "environment"):
                if line.key == key or (flow and mentions_key(key, line.value)):
                    refuse(top)
    return found


def looks_secret(key):
    upper = key.upper()
    return any(word in upper for word in SECRET_WORDS)


def problems(template):
    """meshTerm's TemplateSanity.problems: a list of strings; any one hides the template."""
    found = []
    reported = set()
    reserved_reported = set()
    for issue in validate(template):
        found.append(f"invalid: {issue}")
    # validateStrict's rule 21 (case-sensitive) is a subset of meshTerm's below, which runs too.

    def text(value, field, limit, newlines=False):
        if len(value) > limit:
            found.append(f"{field} is longer than {limit} characters")
        if has_control_characters(value, newlines):
            found.append(f"{field} has a control, separator or bidirectional formatting character")

    text(template["name"], "name", NAME_LIMIT)
    text(template["tagline"], "tagline", TAGLINE_LIMIT)
    text(template["category"], "category", CATEGORY_LIMIT)
    text(template["symbol"], "symbol", SYMBOL_LIMIT)
    if len(template["notes"]) > NOTE_COUNT:
        found.append(f"more than {NOTE_COUNT} notes")
    for note in template["notes"]:
        text(note, "a note", NOTE_LIMIT, newlines=True)
    if len(template["variables"]) > VARIABLE_COUNT:
        found.append(f"more than {VARIABLE_COUNT} variables")
    for variable in template["variables"]:
        key = variable["key"]
        text(variable["label"], f"{key} label", LABEL_LIMIT)
        text(variable["defaultValue"], f"{key} default", DEFAULT_LIMIT)
        if variable.get("help") is not None:
            text(variable["help"], f"{key} help", HELP_LIMIT)
        for option in variable.get("options") or []:
            text(option["text"], f"{key} option text", LABEL_LIMIT)
            text(option["value"], f"{key} option value", DEFAULT_LIMIT)
        if is_reserved_key(key) and key not in reserved_reported:
            reserved_reported.add(key)
            found.append(f"rule 21: variable key {key} is set by the login session or read by compose "
                         f"(rename it, e.g. APP_{key})")
    compose = template["compose"]
    if len(compose.encode("utf-8")) > COMPOSE_BYTES:
        found.append(f"compose is larger than {COMPOSE_BYTES} bytes")
    if has_control_characters(compose, True):
        found.append("compose has a control, separator or bidirectional formatting character")
    declared = {v["key"] for v in template["variables"]}
    values = []
    for variable in template["variables"]:
        values.append(variable["defaultValue"])
        values.extend(o["value"] for o in variable.get("options") or [])
    for name in [n for t in [compose] + values for n in placeholder_names(t)]:
        if name not in declared and name not in reported:
            reported.add(name)
            found.append(f"rule 21: ${name} is interpolated but not declared as a variable "
                         f"(compose would read it from the host's environment)")
    for number, key in refusals(compose):
        found.append(f"compose line {number}: refused form {key!r}")
    return found


def catalogue_rules(template):
    """CI-only rules (plan 4.3 items 4 and 7): brand-neutral text, no dashes in display text, no
    published secret default. A list of strings."""
    found = []
    display = [("name", template["name"]), ("tagline", template["tagline"]), ("category", template["category"])]
    display += [("a note", n) for n in template["notes"]]
    for variable in template["variables"]:
        key = variable["key"]
        display.append((f"{key} label", variable["label"]))
        if variable.get("help") is not None:
            display.append((f"{key} help", variable["help"]))
        for option in variable.get("options") or []:
            display.append((f"{key} option text", option["text"]))
        credential = variable.get("credential") or {}
        if credential.get("display"):
            display.append((f"{key} credential display", credential["display"]))
    for field, value in display:
        for dash, word in DASHES.items():
            if dash in value:
                found.append(f"{field} has an {word} (use a colon, comma or full stop)")
    everything = display + [("symbol", template["symbol"]), ("id", template["id"]), ("compose", template["compose"])]
    for variable in template["variables"]:
        everything.append((f"{variable['key']} default", variable["defaultValue"]))
        everything += [(f"{variable['key']} option value", o["value"]) for o in variable.get("options") or []]
    for field, value in everything:
        if BRAND.search(value):
            found.append(f"{field} names an app ({BRAND.search(value).group(0)!r}); the catalogue serves "
                         f"both apps, so its text stays neutral")
    for variable in template["variables"]:
        credential = variable.get("credential") or {}
        secret = variable["isSecret"] or looks_secret(variable["key"]) or credential.get("field") == "password" \
            or "generate" in variable
        if secret and variable["defaultValue"] and not variable["isPreset"]:
            found.append(f"{variable['key']} is a secret with a published default (a public password); "
                         f"leave it blank so the app generates one")
    return found
