---
name: pr-diff-explain
description: >-
  Writes a review comment on every diff block of a GitHub pull request
  or GitLab merge request. A very large block, such as a new file, can
  get several comments, one per piece, so reviewers can understand AI-written changes
  without re-reading the product or the codebase. A full comment is concise
  pseudocode that keeps every changed name, literal, and operator, with each
  name's purpose in parentheses, plus a short product or
  codebase-pattern note when one exists, and a small Mermaid diagram only
  when the flow is still hard to see. Repeated behaviour gets "This was
  already explained" with a link and no second write-up. If that
  review is already on the pull request, tell the user and stop. On a
  big pull request, spawn sub-agents and post their drafts yourself. Run only inside
  the git repo that contains the change. If gh or glab is missing or not
  logged in, offer to install it and start login. Use when the user
  asks to explain a PR or MR, comment on a diff, add pseudocode review
  comments, reduce review fatigue, or walk pull request changes.
license: MIT
compatibility: Requires Python 3, a local checkout of the change's repo, and a logged-in GitHub CLI (gh) or GitLab CLI (glab).
metadata:
  version: "1.9.0"
---

# PR diff explain

Explain a GitHub pull request or a GitLab merge request. Do not review it for style, bugs, or approval.

A **diff block** is one `@@` hunk. A small block gets one comment. A very large block gets several comments, one per piece. A new file is the usual case. The comment sits on the first changed line of that block or piece only. It does not span the later lines.

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
- Evidence over assumptions. A confirmed product line states the behaviour. A guess is marked **Inferred**. Never present a guess as product fact. The comment does not name a source.
- Low noise. Same behaviour is explained once. Later blocks only point back.
- Match behaviour, not formatting. Two different blocks can be the same check. Two similar `if`s can be different checks.
- Explain in dependency order. A helper or shared check is explained before the blocks that use it. The first block in that order gets the full note.

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
5. On a big pull request, follow "Big pull requests". Sub-agents do steps 6 to 9 for their blocks. The delegator joins repeated behaviour across those drafts and does step 10.
6. Read product context from this repo, only for blocks that change what the product does: title, body, linked issues (`gh issue view` or `glab issue view`), and docs or comments next to the changed symbol on the latest commit of the change.
7. Read codebase context from that same commit, only for those blocks: the changed symbol, and one existing place that already does this job.
8. Order blocks so a definition is before its callers. Group blocks that implement the same behaviour. The earliest block in that group is the full note. The rest are references.
9. Draft every comment locally. Then run the checks below.
10. Post full notes first. Read back their URLs. Post reference notes second, with those URLs. GitHub: [github-posting.md](references/github-posting.md). GitLab: [gitlab-posting.md](references/gitlab-posting.md).
11. Delete the JSON this run created. See "Cleanup".

Re-fetch the latest commit of the change immediately before posting. On a line error, follow that host's retry once. Do not loop.

## Already explained

List comments that contain `PR-DIFF-EXPLAIN AGENT`, `PR-DIFF-EXPLAIN-AGENT`, or `<!-- pr-diff-explain -->`. The list commands are in the posting docs.

A block is already explained when that marker is on the same path and the same first line.

- Every block is already explained. Stop. Tell the user this review is already on the pull request or merge request, and include the url. Do not draft. Do not post.
- Some blocks are already explained. Tell the user which paths are done. Draft and post only the rest.

## Big pull requests

A pull request is big when it has more than 8 diff blocks, or more than about 400 changed lines. The current agent is the delegator. Sub-agents draft. The delegator posts.

1. Drop blocks that are already explained.
2. Group the rest by file. Give each sub-agent about one to four files, and about 8 blocks at most.
3. Spawn one sub-agent per group. Pass the commit sha, that group's block JSON, and these rules: draft full notes only, follow this skill, do not post.
4. The delegator turns repeated behaviour across groups into reference notes, runs "Before posting", and posts.

Example: 20 files become about four sub-agents. The delegator posts one review.

A smaller pull request stays with the current agent. When the host cannot spawn sub-agents, the current agent drafts the big pull request itself and tells the user the work stayed in one agent.

## Cleanup

Delete every JSON file this run wrote. That includes the parsed block list and `review.json`. Delete them after posting, and also when the run stops early. Keep them outside the project while they exist.

## Large diffs

Split a block when one comment would hide later parts. Do this when the block is a new file with more than one piece, or when it has more than about 80 changed lines and more than one piece.

A piece is one function, class, component, or a short group of helpers that belong together. Example: a new `auth.ts` with `login`, `logout`, and `refresh` gets three comments, one on each function. A 12-line bugfix stays one comment.

- Each comment sits on the first changed line of that piece. Take that number from `changed_lines`. Do not set `start_line`. The body still explains the whole piece.
- Its tokens are the names and literals in that piece.
- Pieces do not overlap, and together they cover every changed line in the block.
- Do not split a short block, a lock file, or one straight function.
- Same-behaviour rules still apply. A later piece that repeats an earlier one is a reference note.

## Comment shape

Every comment starts with this line, including references. The comment body starts on the next line. Leave a blank line between the product line, the pattern, and the pseudocode.

```text
PR-DIFF-EXPLAIN AGENT
<comment starts here>
```

GitLab keeps that note. A note that starts with `<` is posted as only `<`.

### Full note

Use a section only when it has something true to say. Omit empty sections.

~~~~markdown
PR-DIFF-EXPLAIN AGENT
<one line of product behaviour>

**Pattern:** <one or two lines>. Current code already does <this>. Same as `<file>`.

```text
<pseudocode>
```
~~~~

If the product claim is not confirmed, replace that line with:

```markdown
**Inferred:** <one line>. Not confirmed in the repo or the PR.
```

A confirmed product line and **Inferred** stay off the same claim. Add Mermaid only under the diagram rule.

- A product line or **Inferred**, never both for the same claim. Skip both when the block does not change product behaviour (rename, format, types only, lockfile).
- **Pattern** only after you have opened an existing example. One or two lines. Name the file. If you did not find one, omit it. Do not invent a pattern.
- Pseudocode is required for source changes.
- Mermaid is optional. See the diagram rule.

### Reference note

Use the user's words. No product line, no pattern, no pseudocode, no diagram.

```markdown
PR-DIFF-EXPLAIN AGENT
This was already explained in <url>. Same <one-line behaviour> reused here.
```

Name the behaviour (`Same daily cap check reused here.`). Do not say "same logic" with no behaviour.

If the URL cannot be matched, still do not repeat the explanation:

```markdown
PR-DIFF-EXPLAIN AGENT
This was already explained on `<path>` line <n>. Same <one-line behaviour> reused here.
```

### Dependency lock files, generated files, format-only

A lock file pins dependency versions (`package-lock.json`, `yarn.lock`, `Gemfile.lock`, `go.sum`, and the same kind of file). Still one comment, so the block is covered. State what changed in one or two lines (package and version, or "indentation only"). Do not annotate every lock-file line. Do not use that short note as the explanation later blocks point at.

## Pseudocode

A reviewer must match the note to the diff token by token.

- Keep every changed name, literal, operator, and call as written. `userId` stays `userId`. `Math.max` stays `Math.max`. `&&` stays `&&`.
- Right after a name, add its purpose in parentheses: `limit (daily cap)`.
- Purpose is the role of that name in this change, in plain words. Do not write only the type (`number`) unless the type is the change.
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
remaining (slots still free) = Math.max(0, limit (daily cap) - used (slots already taken))
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

## Same behaviour

Same behaviour means the same decision, on the same kind of data, for the same outcome.

- Same: two handlers both stop create when `remaining === 0`.
- Not the same: one checks `remaining === 0`, another checks `role === "admin"`.

The full note is the earliest block in dependency order. A helper counts as earlier than its caller.

## Diagram

Add one Mermaid diagram only when the pseudocode still hides the order: several branches, a loop with an early exit, or a handoff across files. Skip a single `if` and any straight-line block.

Use the same names as the diff. About eight nodes or fewer. `flowchart TD`. No styling.

## Before posting

- Every JSON block is covered. A small block is one comment. A split block's comments cover every changed line, with no overlap. `anchor: line` becomes a line comment. `anchor: review_body` is one line in the GitHub review summary, or a GitLab file comment with no line.
- Every full source note includes every token for its own lines. A split comment does not repeat tokens from another piece.
- Reference notes contain `This was already explained` and no pseudocode.
- No second full note for the same behaviour.
- A comment that already has `PR-DIFF-EXPLAIN AGENT`, `PR-DIFF-EXPLAIN-AGENT`, or `<!-- pr-diff-explain -->` on the same path and the same first line is left as-is. One comment on a file's last line does not cover earlier pieces.

Worked examples: [examples.md](references/examples.md).
