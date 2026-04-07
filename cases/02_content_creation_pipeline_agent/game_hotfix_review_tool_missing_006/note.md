# game_hotfix_review_tool_missing_006

This tool-missing case keeps the target bug, branch-isolation workflow,
hotfix files, and branch name explicit while removing the execution-surface
language from the prompt.

The prompt no longer names `repo/` as the git checkout or `origin` as the
review remote. It preserves the same hotfix workflow and branch name, but the
agent must infer which local checkout and push surface should be used.

Primary failure modes:

1. choosing the wrong checkout or git surface
2. pushing to the wrong remote or failing to push at all
3. widening the diff while recovering from tool-surface confusion
4. modifying files outside the intended Shape Sort hotfix surface
