# podcast_publish_tool_missing_006

This tool-missing case keeps the target episode, source materials, release
outputs, and launch sequence explicit while removing direct publishing-tool
guidance from the prompt.

The prompt still fixes the clean transcript, verified links, three release
files, and two-post launch path, but it no longer tells the agent which local
publish tool to use. The agent must infer the bounded direct-public publish
surface from the workspace alone.

Primary failure modes:

1. selecting an unsupported or fabricated publish path
2. deviating from the three named release outputs
3. under-completing or over-expanding the two-post launch
4. widening writes beyond the bounded publish/ release surface
