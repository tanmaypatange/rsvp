"""A small YAML subset reader, so the kit needs no third-party package.

Supported: block mappings, block lists (including lists of mappings),
flow lists [a, b] and flow mappings {k: v} on one line, quoted and plain
scalars, integers, floats, true/false, null or ~, and # comments.
Not supported: anchors, tags, multi-line strings, multiple documents.
Anything outside the subset raises YamlError with the line number.
"""

import re


class YamlError(ValueError):
    pass


_INT = re.compile(r"^[-+]?\d+$")
_FLOAT = re.compile(r"^[-+]?(\d+\.\d*|\.\d+|\d+(\.\d*)?[eE][-+]?\d+)$")


def _strip_comment(line):
    """Remove a trailing # comment that is not inside quotes."""
    out = []
    quote = None
    for i, ch in enumerate(line):
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
            out.append(ch)
            continue
        if ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out).rstrip()


def _scalar(text, lineno):
    t = text.strip()
    if t == "" or t in ("~", "null", "Null", "NULL"):
        return None
    if t[0] in ("'", '"'):
        q = t[0]
        if len(t) < 2 or t[-1] != q:
            raise YamlError("line %d: unterminated quoted string" % lineno)
        body = t[1:-1]
        if q == "'":
            return body.replace("''", "'")
        return (body.replace('\\"', '"').replace("\\n", "\n")
                .replace("\\t", "\t").replace("\\\\", "\\"))
    if t in ("true", "True", "TRUE"):
        return True
    if t in ("false", "False", "FALSE"):
        return False
    if _INT.match(t):
        return int(t)
    if _FLOAT.match(t):
        return float(t)
    if t[0] in "[{":
        return _flow(t, lineno)
    if t[0] in "&*!|>":
        raise YamlError("line %d: unsupported YAML feature %r" % (lineno, t[0]))
    return t


def _flow(text, lineno):
    value, pos = _flow_value(text, 0, lineno)
    if text[pos:].strip():
        raise YamlError("line %d: unexpected text after flow value" % lineno)
    return value


def _skip_ws(text, pos):
    while pos < len(text) and text[pos] in " \t":
        pos += 1
    return pos


def _flow_value(text, pos, lineno):
    pos = _skip_ws(text, pos)
    if pos >= len(text):
        raise YamlError("line %d: unexpected end of flow value" % lineno)
    ch = text[pos]
    if ch == "[":
        items = []
        pos = _skip_ws(text, pos + 1)
        if pos < len(text) and text[pos] == "]":
            return items, pos + 1
        while True:
            item, pos = _flow_value(text, pos, lineno)
            items.append(item)
            pos = _skip_ws(text, pos)
            if pos < len(text) and text[pos] == ",":
                pos += 1
                continue
            if pos < len(text) and text[pos] == "]":
                return items, pos + 1
            raise YamlError("line %d: expected , or ] in flow list" % lineno)
    if ch == "{":
        result = {}
        pos = _skip_ws(text, pos + 1)
        if pos < len(text) and text[pos] == "}":
            return result, pos + 1
        while True:
            key, pos = _flow_token(text, pos, lineno, stop=":")
            pos = _skip_ws(text, pos)
            if pos >= len(text) or text[pos] != ":":
                raise YamlError("line %d: expected : in flow mapping" % lineno)
            val, pos = _flow_value(text, pos + 1, lineno)
            result[str(_scalar(key, lineno))] = val
            pos = _skip_ws(text, pos)
            if pos < len(text) and text[pos] == ",":
                pos += 1
                continue
            if pos < len(text) and text[pos] == "}":
                return result, pos + 1
            raise YamlError("line %d: expected , or } in flow mapping" % lineno)
    token, pos = _flow_token(text, pos, lineno, stop=",]}")
    return _scalar(token, lineno), pos


def _flow_token(text, pos, lineno, stop):
    pos = _skip_ws(text, pos)
    start = pos
    if pos < len(text) and text[pos] in ("'", '"'):
        q = text[pos]
        pos += 1
        while pos < len(text):
            if text[pos] == q:
                if q == "'" and pos + 1 < len(text) and text[pos + 1] == "'":
                    pos += 2
                    continue
                if q == '"' and text[pos - 1] == "\\":
                    pos += 1
                    continue
                return text[start:pos + 1], pos + 1
            pos += 1
        raise YamlError("line %d: unterminated quoted string" % lineno)
    while pos < len(text) and text[pos] not in stop:
        if stop == ":" and text[pos] in ",]}":
            break
        pos += 1
    return text[start:pos].strip(), pos


def _split_key(content, lineno):
    """Split 'key: value' at the first ': ' or trailing ':' outside quotes."""
    quote = None
    for i, ch in enumerate(content):
        if quote:
            if ch == quote:
                quote = None
            continue
        if ch in ("'", '"') and i == 0:
            quote = ch
            continue
        if ch == ":" and (i + 1 == len(content) or content[i + 1] in " \t"):
            key = content[:i].strip()
            if key and key[0] in ("'", '"'):
                key = _scalar(key, lineno)
            return key, content[i + 1:].strip()
    return None, None


def loads(text):
    lines = []
    for n, raw in enumerate(text.splitlines(), start=1):
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise YamlError("line %d: tabs are not allowed for indentation" % n)
        stripped = _strip_comment(raw)
        if not stripped.strip():
            continue
        if stripped.strip() in ("---", "..."):
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        lines.append((indent, stripped.strip(), n))
    if not lines:
        return {}
    value, pos = _block(lines, 0, lines[0][0])
    if pos != len(lines):
        raise YamlError("line %d: unexpected indentation" % lines[pos][2])
    return value


def _block(lines, pos, indent):
    if lines[pos][1].startswith("- ") or lines[pos][1] == "-":
        return _block_list(lines, pos, indent)
    return _block_map(lines, pos, indent)


def _block_list(lines, pos, indent):
    items = []
    while pos < len(lines):
        ind, content, n = lines[pos]
        if ind < indent:
            break
        if ind > indent:
            raise YamlError("line %d: unexpected indentation" % n)
        if not (content.startswith("- ") or content == "-"):
            break
        rest = content[1:].strip()
        if rest == "":
            pos += 1
            if pos < len(lines) and lines[pos][0] > indent:
                value, pos = _block(lines, pos, lines[pos][0])
            else:
                value = None
            items.append(value)
            continue
        key, val = _split_key(rest, n) if rest[0] not in "[{'\"" else (None, None)
        if key is not None:
            # A mapping that starts on the dash line.
            child_indent = ind + 2 + (len(rest) - len(rest.lstrip()))
            sub = [(child_indent, rest, n)]
            j = pos + 1
            while j < len(lines) and lines[j][0] > indent:
                sub.append(lines[j])
                j += 1
            value, used = _block_map(sub, 0, child_indent)
            if used != len(sub):
                raise YamlError("line %d: unexpected indentation" % sub[used][2])
            items.append(value)
            pos = j
            continue
        items.append(_scalar(rest, n))
        pos += 1
    return items, pos


def _block_map(lines, pos, indent):
    result = {}
    while pos < len(lines):
        ind, content, n = lines[pos]
        if ind < indent:
            break
        if ind > indent:
            raise YamlError("line %d: unexpected indentation" % n)
        if content.startswith("- "):
            raise YamlError("line %d: list item where a key was expected" % n)
        key, val = _split_key(content, n)
        if key is None:
            raise YamlError("line %d: expected 'key: value'" % n)
        if key in result:
            raise YamlError("line %d: duplicate key %r" % (n, key))
        pos += 1
        if val == "":
            if pos < len(lines) and lines[pos][0] > indent:
                value, pos = _block(lines, pos, lines[pos][0])
            elif (pos < len(lines) and lines[pos][0] == indent
                  and lines[pos][1].startswith("- ")):
                value, pos = _block_list(lines, pos, indent)
            else:
                value = None
            result[key] = value
        else:
            result[key] = _scalar(val, n)
    return result, pos


def load(path):
    with open(path, "r", encoding="utf-8") as fh:
        return loads(fh.read())
