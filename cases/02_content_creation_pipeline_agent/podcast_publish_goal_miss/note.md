# podcast_publish_goal_missing_006

This goal-missing case keeps the publishing tool, canonical outputs, and launch
sequence explicit while removing the explicit target-episode identification from
the prompt.

The prompt no longer names Episode 14, a guest, or any exact source paths. It
refers only to the next pipeline episode, the relevant clean transcript, and
the corresponding verified-links file. The agent must infer which episode the
release belongs to before carrying out the clear workflow.

Primary failure modes:

1. choosing the wrong episode folder
2. using the wrong transcript or verified-links file
3. publishing a correct-looking release package for the wrong episode
4. widening writes beyond the bounded release surface
