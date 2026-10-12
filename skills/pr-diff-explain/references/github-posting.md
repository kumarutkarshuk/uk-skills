# Posting the comments

Use `gh` from the pull request repo, after the host and repo checks in `SKILL.md`. Post one review of the pseudocode comments. Write `review.json` with `mktemp` outside the project. Delete it after the post, and also if the post fails.

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

Skip a line comment when `body` contains `PR-DIFF-EXPLAIN-AGENT`, `PR-DIFF-EXPLAIN AGENT:`, or `<!-- pr-diff-explain -->`, and `path` plus `line` (the first line of that block or piece) match. A comment on a file's last line does not cover earlier pieces of a large diff.

## Review 1 — full notes only

`event` is `COMMENT`. The review `body` is required:

```text
Pseudocode on each diff block.
```

Add one extra sentence for each `review_body` block (binary, rename with no hunk): path and what changed.

```bash
gh api --method POST repos/<owner>/<repo>/pulls/<number>/reviews --input review.json
```

```json
{
  "commit_id": "<headRefOid>",
  "event": "COMMENT",
  "body": "Pseudocode on each diff block.",
  "comments": [
    {
      "path": "src/limit.ts",
      "body": "PR-DIFF-EXPLAIN-AGENT\n...",
      "side": "RIGHT",
      "line": 2
    }
  ]
}
```

Do not send `start_line` or `start_side`. The comment sits on the first changed line only.

`side` is `RIGHT` for additions and `LEFT` for deletion-only blocks. `line` is the parser's first changed line. A split comment uses the first `changed_lines` number of its own piece. Do not invent a line.

If the payload is rejected for size, split this review into batches of 20 comments.

## 422 retry, once

| API message | What to change |
| --- | --- |
| Line is not part of the diff | Set `line` to the next changed line in that piece from `changed_lines`. Do not add `start_line`. |
| A line range was sent | Drop `start_line` and `start_side`. Keep `line` as the first changed line. |
| Commit outdated | Re-fetch `headRefOid` and the diff, re-parse, post again once. |

If the second try fails, leave that block in the chat output and say it was not posted. Do not attach it to a different file.
