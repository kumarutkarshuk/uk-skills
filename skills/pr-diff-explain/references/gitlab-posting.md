# Posting on GitLab

Use `glab` 1.94.0 or newer from the merge request repo, after the host and repo checks in `SKILL.md`. Line comments need `mr note create --line`, shipped in that release. Post full notes first, then reference notes, so the second set can link to real URLs.

Do not run `glab mr approve`.

Write each comment body to a file from `mktemp`, outside the project. Delete it after the call.

## Load the merge request

```bash
glab mr diff <id> --raw
glab api "projects/:id/merge_requests/<id>"
```

Use `sha` as the latest commit. Use `title`, `description`, and `web_url` from that JSON.

## Skip notes this skill already left

```bash
glab api "projects/:id/merge_requests/<id>/discussions"
```

Skip a note when its body contains `PR-DIFF-EXPLAIN-AGENT` or `<!-- pr-diff-explain -->`, and the discussion position matches that path and the first line of that block or piece. A note on a file's last line does not cover earlier pieces of a large diff.

## Full notes

The note sits on the first changed line only. Do not pass a start:end range. A split comment uses the first `changed_lines` number of its own piece. The body starts with `PR-DIFF-EXPLAIN-AGENT`. Pass it quoted from the temp file so the shell does not cut the note at `<`.

```bash
glab mr note create <id> --file <path> --line <line> -m "$(cat "$note")"
```

Removed lines only. `--old-line` takes one line. Pass the first removed line. The body still explains the whole block.

```bash
glab mr note create <id> --file <path> --old-line <line> -m "$(cat "$note")"
```

A block with `anchor: review_body` is a file comment. Pass `--file` and no line flag. If the path is unknown, omit `--file` and put the path in the body.

## Reference notes

List discussions again. The link is `<web_url>#note_<note id>`.

Post the reference sentence with `glab mr note create` on that block's file and line. Same line flags as a full note.

## Retry once

If GitLab says the line is not in the diff, post again on the next changed line in that piece. Do not send a line range. If the second try fails, leave that block in the chat and say it was not posted.
