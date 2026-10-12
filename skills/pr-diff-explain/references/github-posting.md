# Posting the comments

Use `gh` from the pull request repo, after the host and repo checks in `SKILL.md`. Post two reviews so reference notes can link to real comment URLs. Write `review.json` with `mktemp` outside the project, then delete it.

## Identity

```bash
gh pr view <number> --json number,url,title,body,headRefOid
gh repo view --json nameWithOwner --jq .nameWithOwner
```

`commit_id` is `headRefOid` fetched immediately before the POST.

## Skip blocks already explained by this skill

```bash
gh api --paginate repos/<owner>/<repo>/pulls/<number>/comments \
  --jq '.[] | {path, line, side, html_url, body}'
```

Skip a line comment when `body` contains `<!-- pr-diff-explain -->` and `path` plus `line` (the end line) match the block.

## Review 1 — full notes only

`event` is `COMMENT`. The review `body` is required:

```text
Pseudocode on each diff block. Repeated behaviour points at the first explanation.
```

Add one extra sentence for each `review_body` block (binary, rename with no hunk): path and what changed.

```bash
gh api --method POST repos/<owner>/<repo>/pulls/<number>/reviews --input review.json
```

```json
{
  "commit_id": "<headRefOid>",
  "event": "COMMENT",
  "body": "Pseudocode on each diff block. Repeated behaviour points at the first explanation.",
  "comments": [
    {
      "path": "src/limit.ts",
      "body": "<!-- pr-diff-explain -->\n...",
      "side": "RIGHT",
      "start_side": "RIGHT",
      "start_line": 2,
      "line": 4
    }
  ]
}
```

Omit `start_line` and `start_side` when the block has no `start_line` (single changed line).

`side` is `RIGHT` for additions and `LEFT` for deletion-only blocks. Line numbers come from the parser. Do not invent them.

If the payload is rejected for size, split this review into batches of 20 comments. Finish every full-note batch before any reference note.

## Review 2 — reference notes

List comments again. Match each full note by `path`, `line`, and the marker. Put that `html_url` in the reference sentence.

Post a second `COMMENT` review with only the reference comments. Review body:

```text
Pointers to explanations already posted on this PR.
```

## 422 retry, once

| API message | What to change |
| --- | --- |
| Line is not part of the diff | Set `line` to a changed line from `added` or `removed` inside that block. Drop `start_line` if it was the rejected end. |
| `start_line` invalid | Drop `start_line` and `start_side`. Keep the end `line`. |
| Commit outdated | Re-fetch `headRefOid` and the diff, re-parse, post again once. |

If the second try fails, leave that block in the chat output and say it was not posted. Do not attach it to a different file.
