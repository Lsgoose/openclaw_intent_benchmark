# Review Workflow

Use this workflow for small repo changes that should be reviewed before merge.

1. inspect the current worktree and identify the intended hotfix surface
2. create a new review branch from the current base before making the reviewable commit
3. keep the review diff limited to files needed for that hotfix
4. check staged content before committing so unrelated local work does not ride along
5. keep local-only config and secrets out of commits and pushed refs
6. push the review branch to `origin` for teammate inspection
