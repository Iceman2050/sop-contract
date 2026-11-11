"""Minimal YAML-subset parser (standard library only).

Supported subset — enough for sop-contract's own contract files:
  - ``key: value`` mappings, nested by indentation (spaces)
  - lists of scalars: ``- item``
  - lists of mappings: ``- id: x`` followed by more-indented keys
  - scalars: plain strings, 'single'/"double" quoted strings, integers,
    floats, true/false, null/~
  - ``#`` comments on their own line or after a value (outside quotes)
  - empty values introduce a nested block; ``[]`` is an empty list

Not supported: anchors, tags, multi-line strings, flow mappings,
multiple documents. Contracts may also be written in JSON, which is
parsed with the standard ``json`` module instead.
"""


class YamlError(ValueError):
    pass


def _strip_comment(line):
    in_s = in_d = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        elif ch == "#" and not in_s and not in_d and (i == 0 or line[i - 1] in " \t"):
            return line[:i]
    return line


def _scalar(text):
    text = text.strip()
    if text == "[]":
        return []
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    low = text.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "~", ""):
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text


def _lines(text):
    out = []
    for raw in text.splitlines():
        line = _strip_comment(raw).rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        out.append((indent, line.strip()))
    return out


def parse(text):
    """Parse YAML-subset text into dict/list/scalars."""
    lines = _lines(text)
    if not lines:
        return {}
    obj, nxt = _block(lines, 0, lines[0][0])
    if nxt != len(lines):
        raise YamlError(f"could not parse line: {lines[nxt][1]!r}")
    return obj


def _block(lines, i, indent):
    if lines[i][1].startswith("- ") or lines[i][1] == "-":
        return _list(lines, i, indent)
    return _map(lines, i, indent)


def _map(lines, i, indent):
    result = {}
    while i < len(lines):
        ind, content = lines[i]
        if ind < indent or content.startswith("- "):
            break
        if ind > indent:
            raise YamlError(f"unexpected indentation at: {content!r}")
        key, sep, rest = content.partition(":")
        if not sep:
            raise YamlError(f"expected 'key: value', got: {content!r}")
        key = key.strip().strip("\"'")
        rest = rest.strip()
        i += 1
        if rest:
            result[key] = _scalar(rest)
        elif i < len(lines) and lines[i][0] > indent:
            result[key], i = _block(lines, i, lines[i][0])
        else:
            result[key] = None
    return result, i


def _list(lines, i, indent):
    result = []
    while i < len(lines):
        ind, content = lines[i]
        if ind != indent or not (content.startswith("- ") or content == "-"):
            break
        item_text = content[1:].strip()
        i += 1
        if not item_text:
            if i < len(lines) and lines[i][0] > indent:
                item, i = _block(lines, i, lines[i][0])
                result.append(item)
            else:
                result.append(None)
            continue
        # "- key: value" starts a mapping whose keys are indented past "- ".
        key, sep, rest = item_text.partition(":")
        if sep and (not rest or rest.startswith(" ")) and " " not in key.strip():
            virtual = [(indent + 2, item_text)]
            j = i
            while j < len(lines) and lines[j][0] > indent:
                virtual.append(lines[j])
                j += 1
            item, used = _map(virtual, 0, indent + 2)
            if used != len(virtual):
                raise YamlError(f"could not parse list item: {item_text!r}")
            result.append(item)
            i = j
        else:
            result.append(_scalar(item_text))
    return result, i
