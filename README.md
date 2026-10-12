# uk-skills

Agent skills. Install with the [skills CLI](https://skills.sh/).

## Install

List the skills in this repo:

```bash
npx skills add kumarutkarshuk/uk-skills --list
```

Install every skill:

```bash
npx skills add kumarutkarshuk/uk-skills --all
```

Install one skill. Change the name to the skill you want:

```bash
npx skills add kumarutkarshuk/uk-skills --skill pr-diff-explain
```

## Skills

| Skill | What it does |
| --- | --- |
| [pr-diff-explain](skills/pr-diff-explain/SKILL.md) | Simple pseudocode on every diff piece, on the last line of that piece, plus a pattern line or a diagram when one fits. A very large diff, such as a new file, gets several comments, one per piece. If that review is already posted, it tells you and stops. It counts the diff, spawns that many sub-agents, and the main agent posts. Run it inside the repo that contains the GitHub pull request or GitLab merge request. Offers to install `gh` or `glab` and start login when that tool is missing. It explains changes. It does not approve the PR. |
