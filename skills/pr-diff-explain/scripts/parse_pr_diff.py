#!/usr/bin/env python3
"""Split a pull request diff into one block per hunk.

A small hunk is one review comment. A very large hunk, such as a new file,
can become several comments. Each changed line keeps its number so those
comments can sit on the right piece.
"""

import json
import re
import sys

# Words that are syntax, not names a reviewer must learn.
SYNTAX_WORDS = {
    "and", "or", "not", "in", "of", "if", "else", "elif", "for", "while",
    "switch", "case", "break", "continue", "return", "yield", "try", "catch",
    "throw", "finally", "new", "const", "let", "var", "function", "class",
    "import", "export", "from", "default", "async", "await", "type",
    "interface", "public", "private", "protected", "static", "void", "int",
    "string", "bool", "boolean", "number", "def", "none", "true", "false",
    "null", "undefined", "self", "this", "package", "func", "val", "struct",
    "enum", "impl", "pub", "fn", "mut", "let", "as", "is",
}

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
IDENT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
STRING_RE = re.compile(r'"[^"\n]*"|\'[^\'\n]*\'|`[^`\n]*`')
NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")


def parse_diff(text):
    """Turn a unified diff into comment targets. One target per @@ block."""
    files = []
    current = None
    block = None

    def finish_block():
        nonlocal block
        if current is not None and block is not None:
            current["blocks"].append(_finish(block))
        block = None

    def finish_file():
        nonlocal current
        finish_block()
        if current is not None:
            if not current["blocks"]:
                current["anchor"] = "review_body"
            files.append(current)
        current = None

    for raw in text.splitlines():
        line = raw.rstrip("\r")
        if line.startswith("diff --git "):
            finish_file()
            old, new = _git_paths(line[len("diff --git "):])
            current = {
                "path": new,
                "old_path": old,
                "blocks": [],
                "binary": False,
                "anchor": "line",
            }
            continue
        if current is None:
            continue
        if line.startswith("rename from "):
            current["old_path"] = _strip_path(line[len("rename from "):], "")
            continue
        if line.startswith("rename to "):
            current["path"] = _strip_path(line[len("rename to "):], "")
            continue
        if line.startswith("Binary files "):
            current["binary"] = True
            continue
        if line.startswith("--- "):
            current["old_path"] = _strip_path(line[4:], "a/")
            continue
        if line.startswith("+++ "):
            current["path"] = _strip_path(line[4:], "b/")
            continue
        if line.startswith("@@"):
            finish_block()
            match = HUNK_RE.match(line)
            if not match:
                continue
            block = {
                "header": line,
                "old_start": int(match.group(1)),
                "new_start": int(match.group(3)),
                "old_line": int(match.group(1)),
                "new_line": int(match.group(3)),
                "lines": [],
            }
            continue
        if block is None:
            continue
        if line.startswith("\\"):
            continue
        if line.startswith("+"):
            block["lines"].append({
                "kind": "add",
                "text": line[1:],
                "new_line": block["new_line"],
            })
            block["new_line"] += 1
            continue
        if line.startswith("-"):
            block["lines"].append({
                "kind": "del",
                "text": line[1:],
                "old_line": block["old_line"],
            })
            block["old_line"] += 1
            continue
        text_line = line[1:] if line.startswith(" ") else line
        block["lines"].append({
            "kind": "context",
            "text": text_line,
            "old_line": block["old_line"],
            "new_line": block["new_line"],
        })
        block["old_line"] += 1
        block["new_line"] += 1

    finish_file()
    return _flatten(files)


def _finish(block):
    """Put the comment on the first changed line. Later lines stay in the body only."""
    added = [item for item in block["lines"] if item["kind"] == "add"]
    removed = [item for item in block["lines"] if item["kind"] == "del"]
    # Line numbers let a large new file get one comment per function, on that function's first line.
    record = {
        "header": block["header"],
        "added": [item["text"] for item in added],
        "removed": [item["text"] for item in removed],
        "changed_lines": _changed_lines(
            [item for item in block["lines"] if item["kind"] != "context"]
        ),
        "tokens": _tokens(added + removed),
    }
    if added:
        start = added[0]["new_line"]
        side = "RIGHT"
    elif removed:
        start = removed[0]["old_line"]
        side = "LEFT"
    else:
        record["anchor"] = "review_body"
        return record
    record["anchor"] = "line"
    record["side"] = side
    record["line"] = start
    return record


def _changed_lines(items):
    """Keep each changed line's number so a split comment can name its first line."""
    rows = []
    for item in items:
        row = {"kind": item["kind"], "text": item["text"]}
        if "new_line" in item:
            row["new_line"] = item["new_line"]
        if "old_line" in item:
            row["old_line"] = item["old_line"]
        rows.append(row)
    return rows


def _tokens(items):
    """Names and literals the comment must still show, in first-seen order."""
    seen = []
    found = set()
    for item in items:
        text = item["text"]
        for token in IDENT_RE.findall(text):
            if token.lower() in SYNTAX_WORDS or token in found:
                continue
            found.add(token)
            seen.append(token)
        for token in STRING_RE.findall(text):
            if token not in found:
                found.add(token)
                seen.append(token)
        for token in NUMBER_RE.findall(text):
            if token not in found:
                found.add(token)
                seen.append(token)
    return seen


def _strip_path(raw, prefix):
    """Drop git's a/ or b/ prefix. /dev/null means that side does not exist."""
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1]
    if prefix and raw.startswith(prefix):
        raw = raw[len(prefix):]
    if raw == "/dev/null":
        return None
    return raw


def _git_paths(body):
    """Read old and new paths from a diff --git line, including quoted paths."""
    parts = []
    current = []
    quoted = False
    for char in body.strip():
        if char == '"':
            quoted = not quoted
            continue
        if char == " " and not quoted:
            if current:
                parts.append("".join(current))
                current = []
            continue
        current.append(char)
    if current:
        parts.append("".join(current))
    if len(parts) != 2:
        return None, None
    return _strip_path(parts[0], "a/"), _strip_path(parts[1], "b/")


def _flatten(files):
    blocks = []
    for file_info in files:
        path = file_info["path"] or file_info["old_path"] or "(unknown)"
        if not file_info["blocks"]:
            blocks.append({
                "id": path + "#file",
                "path": path,
                "old_path": file_info["old_path"],
                "anchor": "review_body",
                "binary": file_info["binary"],
                "tokens": [],
                "added": [],
                "removed": [],
            })
            continue
        for index, block in enumerate(file_info["blocks"], start=1):
            block["id"] = f"{path}#{index}"
            block["path"] = path
            block["old_path"] = file_info["old_path"]
            block["binary"] = False
            blocks.append(block)
    return blocks


def self_test():
    """Check the splitter against a few diff shapes reviewers actually see."""
    sample = """diff --git a/src/limit.ts b/src/limit.ts
--- a/src/limit.ts
+++ b/src/limit.ts
@@ -1,3 +1,5 @@
 export function remaining(limit: number, used: number) {
-  return limit - used
+  const remaining = Math.max(0, limit - used)
+  if (remaining === 0) return 0
+  return remaining
 }
diff --git a/src/old.ts b/src/old.ts
--- a/src/old.ts
+++ /dev/null
@@ -2,2 +0,0 @@
-export const gone = true
-export const also = 1
diff --git a/src/pic.bin b/src/pic.bin
Binary files a/src/pic.bin and b/src/pic.bin differ
diff --git a/src/one.ts b/src/one.ts
--- a/src/one.ts
+++ b/src/one.ts
@@ -10 +10,2 @@
-keep
+keep
+extra
"""
    blocks = parse_diff(sample)
    by_id = {block["id"]: block for block in blocks}
    assert list(by_id) == [
        "src/limit.ts#1",
        "src/old.ts#1",
        "src/pic.bin#file",
        "src/one.ts#1",
    ], list(by_id)
    cap = by_id["src/limit.ts#1"]
    assert cap["side"] == "RIGHT" and cap["line"] == 2
    assert "start_line" not in cap
    assert cap["changed_lines"][1]["kind"] == "add" and cap["changed_lines"][1]["new_line"] == 2
    assert "remaining" in cap["tokens"] and "limit" in cap["tokens"]
    assert "0" in cap["tokens"]
    assert "return" not in cap["tokens"]
    gone = by_id["src/old.ts#1"]
    assert gone["side"] == "LEFT" and gone["line"] == 2
    picture = by_id["src/pic.bin#file"]
    assert picture["anchor"] == "review_body" and picture["path"] == "src/pic.bin"
    one = by_id["src/one.ts#1"]
    assert one["side"] == "RIGHT" and one["line"] == 10
    print("ok")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        self_test()
        return
    if len(sys.argv) > 1 and sys.argv[1] != "-":
        with open(sys.argv[1], encoding="utf-8") as handle:
            text = handle.read()
    else:
        text = sys.stdin.read()
    json.dump(parse_diff(text), sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
