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

Skip a piece when `body` contains `PR-DIFF-EXPLAIN-AGENT`, `PR-DIFF-EXPLAIN AGENT:`, or `<!-- pr-diff-explain -->`, and `path` matches, and `line` is any changed line of that piece. The new comment still sits on the last changed line. A comment on a later piece does not cover earlier pieces.

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
      "line": 4
    }
  ]
}
```

Do not send `start_line` or `start_side`. The comment sits on the last changed line only.

`side` follows that last line: `RIGHT` when it is an addition, `LEFT` when it is a deletion. `line` is the parser's last changed line. A split comment uses the last `changed_lines` number of its own piece. Do not invent a line.

If the payload is rejected for size, split this review into batches of 20 comments.

## 422 retry, once

| API message | What to change |
| --- | --- |
| Line is not part of the diff | Set `line` to the previous changed line in that piece from `changed_lines`. Walk back from the end. Do not add `start_line`. |
| A line range was sent | Drop `start_line` and `start_side`. Keep `line` as the last changed line. |
| Commit outdated | Re-fetch `headRefOid` and the diff, re-parse, post again once. |

If the second try fails, leave that block in the chat output and say it was not posted. Do not attach it to a different file.
