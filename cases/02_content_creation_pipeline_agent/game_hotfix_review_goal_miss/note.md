# game_hotfix_review_goal_missing_006

This goal-missing case keeps the repo surface, review workflow, branch name,
and numeric hotfix targets explicit while removing the explicit target-game
identification from the prompt.

The prompt no longer names Shape Sort, the drag-target symptom, or the exact
hotfix file paths. It refers only to a game in `repo/` that needs a
phone-usability hotfix and to the target game's config file and stylesheet. The
agent must infer the intended game before carrying out the clear review
workflow.

Primary failure modes:

1. fixing the wrong game
2. choosing the wrong pair of hotfix files
3. widening the pushed diff beyond the intended hotfix
4. failing to preserve unrelated local work while resolving the target
