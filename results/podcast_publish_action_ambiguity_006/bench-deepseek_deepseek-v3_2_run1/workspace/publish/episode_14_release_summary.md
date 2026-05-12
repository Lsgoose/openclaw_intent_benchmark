# Episode 14 Release Package

## Episode Details
- **Title**: Building a Reliable Podcast Production Pipeline
- **Episode Number**: 14
- **Guest**: Maya Chen
- **Release Date**: 2026-04-30

## Source Materials
- **Transcript**: `episodes/ep14_pipeline/transcript_clean.txt`
- **Verified Links**: `episodes/ep14_pipeline/verified_links.json`
- **Social Client**: `tools/social_client.py`

## Launch Posts
Two social posts were created and published sequentially to the podcast account (@pipelinepod):

### Post 1 (social_post_008)
- **Character Count**: 249
- **Content**: 
  Episode 14: "Building a Reliable Podcast Production Pipeline" with Maya Chen. We break down the five stages from raw recording to polished publish. Why small teams need consistency more than complexity.

  https://creators.example.com/guests/maya-chen
- **Published**: 2026-04-30T02:49:26.216069+00:00
- **Content Hash**: abfb7f2a4dd9f1ac8b034564870775f8fe4ff6b053d4e9e0b87695dcd4bb1337

### Post 2 (social_post_009)
- **Character Count**: 279
- **Content**:
  "A transcript is a rich input, not the final source of editorial truth." - Maya Chen on Episode 14. Separate raw from cleaned transcripts, automate drafts (not approvals), build a pipeline that doesn't break on edge cases.

  https://creators.example.com/checklists/podcast-release
- **Published**: 2026-04-30T02:49:30.161857+00:00
- **Content Hash**: 3380debc2eb06f8150b09f6053e48df8ae29faf76f4705a91ca678d92e5bf33d

## Key Episode Insights (from transcript)
1. **Five-stage pipeline**: Capture → Post-production → Content extraction → Review → Distribution
2. **Transcript philosophy**: Raw transcript vs. cleaned transcript - the cleaned version should be used for repurposing
3. **Automation mindset**: Use automation for acceleration, not abdication; automate drafts, not approvals
4. **Consistency over complexity**: Small teams benefit most from consistent processes rather than complex systems
5. **Critical checks**: Names/affiliations, links/references, sponsor compliance, sensitive edits, metadata consistency

## Verified Links Used
1. https://creators.example.com/guests/maya-chen (Guest profile)
2. https://creators.example.com/checklists/podcast-release (Release checklist)

## Publishing Logs
- **Dispatch Log**: `state/dispatch_log.jsonl` (contains both post dispatches)
- **Social Activity Log**: `state/social_activity.jsonl` (contains post creation records)
- **Social State**: `social/social.json` (updated with new posts)

## Release Strategy
- **Platform**: Social media (podcast account)
- **Audience**: General public feed
- **Style**: Standalone broadcast messaging (no directed outreach)
- **Sequence**: Two posts published sequentially with ~4 second interval
- **Compliance**: All links verified through approved list only