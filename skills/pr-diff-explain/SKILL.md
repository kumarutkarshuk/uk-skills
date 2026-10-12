---
name: pr-diff-explain
description: >-
  Writes a review comment on every diff block of a GitHub pull request
  or GitLab merge request. The comment sits on the last changed line of
  that block or piece. A very large block, such as a new file, can
  get several comments, one per piece, so reviewers can understand AI-written changes
  without re-reading the product or the codebase. A full comment is concise
  pseudocode in simple Indian English. It keeps every changed name, literal,
  and operator, with each name's purpose in parentheses. Add a pattern line
  or a diagram when one fits the change.
  If that review is already on the pull request, tell the user and stop.
  Count the diff, then spawn that many sub-agents and post their drafts
  yourself. Run only inside
  the git repo that contains the change. If gh or glab is missing or not
  logged in, offer to install it and start login. Use when the user
  asks to explain a PR or MR, comment on a diff, add pseudocode review
  comments, reduce review fatigue, or walk pull request changes.
license: MIT
compatibility: Requires Python 3, a local checkout of the change's repo, and a logged-in GitHub CLI (gh) or GitLab CLI (glab).
metadata:
  version: "1.13.0"
---

# PR diff explain

Explain a GitHub pull request or a GitLab merge request. Do not review it for style, bugs, or approval.

A **diff block** is one `@@` hunk. A small block gets one comment. A very large block gets several comments, one per piece. A new file is the usual case. The comment sits on the last changed line of that block or piece only. It does not span the earlier lines.

## Host tool

Pick the tool from the git remote, or from the link the user pasted.

- GitHub (`github.com`, or a pull request link): `gh`
- GitLab (host contains `gitlab`, or a `/-/merge_requests/` link): `glab`

If the host is unclear, ask the user. Do not guess.

```bash
command -v gh && gh auth status
command -v glab && glab auth status
```

If the needed tool is missing, or login fails, stop the review. Offer to install it and start login. Install only after the user says yes. Login is interactive, so start it and let the user finish in the terminal.

- Missing `gh`: offer `brew install gh` on macOS, or https://cli.github.com/ on another system. Then offer `gh auth login`.
- Missing `glab`: offer `brew install glab` on macOS, or https://gitlab.com/gitlab-org/cli on another system. Then offer `glab auth login`. If the host is not gitlab.com, use `glab auth login --hostname <host>`.
- Tool is installed but not logged in: offer to start the login command. Do not reinstall.

GitLab line comments need `glab mr note create --line`. Official docs document `--line` and `--old-line`: https://docs.gitlab.com/cli/mr/note/create/. That flag shipped in glab 1.94.0 (`feat(mr): create diff comments`, https://gitlab.com/gitlab-org/cli/-/releases/v1.94.0). Older `glab` can have `mr note create` and still lack `--line`.

Check `glab mr note create --help` for `--line`. If it is missing, offer to upgrade (`brew upgrade glab` on macOS). Do not post line notes as a general comment. After an upgrade, check the flag again.

## Where this runs

Run in the project folder that contains the change. Read that project's docs and code. This skill folder is not that project.

1. `git rev-parse --show-toplevel` must succeed.
2. The remote must be the same project as the change. GitHub: `gh repo view --json nameWithOwner` equals the pull request `owner/repo`. GitLab: `glab repo view` is the merge request's project.
3. If not, stop. Tell the user which folder to open. Do not post. Do not explain from the diff alone. Do not clone.

Read docs and nearby code from the latest commit on that pull request or merge request branch. GitHub calls it `headRefOid`. GitLab calls it `sha`. Use `git show <sha>:<path>` and `git grep` on that commit. Do not read a different branch that happens to be checked out.

## Rules

- Accuracy over brevity. Never drop a condition, argument, default, or early exit to make the note shorter.
- Evidence over assumptions. A name's purpose in parentheses matches the code. Never add a purpose that the diff does not support.
- Each piece gets its own pseudocode. A pattern line or a diagram is extra, and only when it fits.
- Match behaviour, not formatting. Two similar `if`s can be different checks.

## When not to post

If the user says draft, preview, or don't post: print the comment bodies and stop.

Never use `APPROVE` or `REQUEST_CHANGES`. The review event is `COMMENT`.

Do not suggest refactors. Do not write "LGTM".

## Workflow

1. Pass "Host tool" and "Where this runs".
2. Load the change in that repo. GitHub: `gh pr view <number> --json number,url,title,body,headRefOid` and `gh pr diff <number>`. GitLab: `glab mr diff <id> --raw`, and `glab api "projects/:id/merge_requests/<id>"` for `title`, `description`, and `sha`.
3. Split the diff. From this skill directory, run:

```bash
python3 scripts/parse_pr_diff.py < pr.diff
```

The JSON is the full block list. Do not skip an object because it looks small. A small object gets one comment. A very large object is split under "Large diffs". `changed_lines` holds each changed line and its number.

4. Check "Already explained". If the review is already done, stop there.
5. Count the diff and follow "How many sub-agents". Spawn that many. Sub-agents do steps 6 to 9 for their blocks. The delegator posts in step 10.
6. Read the changed symbol on the latest commit of the change, and one existing place that already does this job, so the pattern line can name that file.
7. Draft pseudocode for every piece. Add a pattern line or a diagram only when it fits.
8. Keep parser order.
9. Draft every comment locally. Then run the checks below.
10. Post the pseudocode comments. GitHub: [github-posting.md](references/github-posting.md). GitLab: [gitlab-posting.md](references/gitlab-posting.md).
11. Delete the JSON this run created. See "Cleanup".

Re-fetch the latest commit of the change immediately before posting. On a line error, follow that host's retry once. Do not loop.

## Already explained

List comments that contain `PR-DIFF-EXPLAIN-AGENT`, `PR-DIFF-EXPLAIN AGENT:`, or `<!-- pr-diff-explain -->`. The list commands are in the posting docs.

A block or piece is already explained when that marker is on the same path and on any changed line of that piece. The new comment still sits on the last changed line. A marker on a later piece does not cover earlier pieces.

- Every block is already explained. Stop. Tell the user this review is already on the pull request or merge request, and include the url. Do not draft. Do not post.
- Some blocks are already explained. Tell the user which paths are done. Draft and post only the rest.

## How many sub-agents

Count after dropping blocks that are already explained.

- `B` is the number of blocks left.
- `L` is the number of changed lines in those blocks.
- `from_blocks` is `(B + 7) // 8`.
- `from_lines` is `(L + 399) // 400`.
- `agents` is the larger of `from_blocks` and `from_lines`.

Tell the user `B`, `L`, and `agents` before any spawn.

When `agents` is 1, the current agent drafts. Spawn none.

When `agents` is more than 1, the current agent is the delegator. Spawn exactly `agents` sub-agents. In parser order, the first `B % agents` sub-agents get `(B // agents) + 1` blocks. The rest get `B // agents` blocks. Pass the commit sha, that group's block JSON, and these rules: pseudocode is required, add a pattern line or a diagram only when it fits, follow this skill, do not post. The delegator checks the drafts and posts.

Example: 20 blocks and 500 changed lines. `from_blocks` is 3, `from_lines` is 2, so spawn 3. Group sizes are 7, 7, and 6.

When the host cannot spawn sub-agents, the current agent drafts the pull request itself and tells the user the work stayed in one agent.

## Cleanup

Delete every JSON file this run wrote. That includes the parsed block list and `review.json`. Delete them after posting, and also when the run stops early. Keep them outside the project while they exist.

## Large diffs

Split a block when one comment would hide later parts. Do this when the block is a new file with more than one piece, or when it has more than about 80 changed lines and more than one piece.

A piece is one function, class, component, or a short group of helpers that belong together. Example: a new `auth.ts` with `login`, `logout`, and `refresh` gets three comments, one on each function. A 12-line bugfix stays one comment.

- Each comment sits on the last changed line of that piece. Take that number from `changed_lines`. Do not set `start_line`. The body still explains the whole piece.
- Its tokens are the names and literals in that piece.
- Pieces do not overlap, and together they cover every changed line in the block.
- Do not split a short block, a lock file, or one straight function.
- Each piece gets its own pseudocode.

## Comment shape

Every comment starts with this line. The pseudocode starts on the next line. If a new line after the marker is not possible, use `PR-DIFF-EXPLAIN AGENT:` and start the pseudocode after the colon.

```text
PR-DIFF-EXPLAIN-AGENT
<pseudocode starts here>
```

GitLab keeps that note. A note that starts with `<` is posted as only `<`.

### Full note

Pseudocode is required. Add **Pattern** only after you have opened an existing example. One or two lines. Name the file. Omit it when you did not find one. Add one diagram only when the pseudocode still hides the order.

~~~~markdown
PR-DIFF-EXPLAIN-AGENT
```text
<pseudocode>
```

**Pattern:** <one or two lines>. Current code already does <this>. Same as `<file>`.
~~~~

- A rename, format-only change, or lock file still gets one comment. For a lock file, list the package and version as lines. Skip pattern and diagram there.

### Dependency lock files, generated files, format-only

A lock file pins dependency versions (`package-lock.json`, `yarn.lock`, `Gemfile.lock`, `go.sum`, and the same kind of file). Still one comment, so the block is covered. List package and version as lines. Do not annotate every lock-file line.

## Pseudocode

A reviewer must match the note to the diff token by token. The words you add must stay very simple.

- Keep every changed name, literal, operator, and call as written. `userId` stays `userId`. `Math.max` stays `Math.max`. `&&` stays `&&`.
- Right after a name, add its purpose in parentheses: `limit (max in one day)`.
- Purpose is the role of that name in this change, in simple Indian English. Short everyday words. A new teammate should get it in one read. `limit (max in one day)` is good. `limit (per-diem instantiation quota)` is not. Do not write only the type (`number`) unless the type is the change.
- Annotate a name the first time it appears in that comment. Repeat the purpose only when a later use could be mixed up with another name.
- Keep argument order, defaults, and early exits.
- One short line per step, in execution order.
- Write Python-like lines. An `if` is its own line. The action is indented on the next line. No braces. No action on the `if` line.
- Do not add behaviour that is not in the diff.
- The `tokens` array on the block is the checklist. Every token appears in the pseudocode, outside the parentheses.

```text
if user in db
      do something
```

```text
remaining (slots still left) = Math.max(0, limit (max in one day) - used (slots already taken))
if remaining === 0
      return 0
return remaining
```

That matches:

```ts
const remaining = Math.max(0, limit - used)
if (remaining === 0) return 0
return remaining
```

## Diagram

Add one Mermaid diagram only when the pseudocode still hides the order: several branches, a loop with an early exit, or a handoff across files. Skip a single `if` and any straight-line block.

Use the same names as the diff. About eight nodes or fewer. `flowchart TD`. No styling.

## Before posting

- Every JSON block is covered. A small block is one comment. A split block's comments cover every changed line, with no overlap. `anchor: line` becomes a line comment. `anchor: review_body` is one line in the GitHub review summary, or a GitLab file comment with no line.
- Every full source note includes every token for its own lines. A split comment does not repeat tokens from another piece.
- Every source comment includes pseudocode. Pattern and diagram appear only when they fit that piece.
- A comment that already has `PR-DIFF-EXPLAIN-AGENT`, `PR-DIFF-EXPLAIN AGENT:`, or `<!-- pr-diff-explain -->` on the same path and on any changed line of that piece is left as-is. One comment on a later piece does not cover earlier pieces.

Worked examples: [examples.md](references/examples.md).
