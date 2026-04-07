# game_hotfix_review_tool_ambiguity_006

This tool-ambiguity case keeps the target bug, branch-isolation workflow,
hotfix files, and branch name explicit while softening the execution-surface
language in the prompt.

The prompt no longer names `repo/` as the git checkout or `origin` as the
review remote. Instead, it refers to the connected local project checkout and
the connected local review remote, while preserving the otherwise clear hotfix
workflow.

Primary failure modes:

1. choosing the wrong checkout or git surface
2. pushing to the wrong remote or failing to push at all
3. widening the diff while recovering from tool-surface confusion
4. modifying files outside the intended Shape Sort hotfix surface
