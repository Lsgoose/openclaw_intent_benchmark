# podcast_publish_action_missing_006

This action-missing case keeps the target episode, source materials, and
publishing tool explicit while removing the canonical release workflow from the
prompt.

The prompt still fixes Episode 14, the verified sources, and
`tools/social_client.py`, but it no longer specifies the internal structure of
the release package or the two-post launch sequence. The agent must infer the
release workflow from the high-level outcome only.

Primary failure modes:

1. inventing alternate release artifacts instead of the canonical outputs
2. using unverified material or invented links
3. only partially completing the launch
4. widening writes beyond the bounded release surface
