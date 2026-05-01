# Episode 14 Release Checklist ✅

## ✅ Source Materials Verified
- [x] Transcript source: `episodes/ep14_pipeline/transcript_clean.txt`
- [x] Verified links: `episodes/ep14_pipeline/verified_links.json`
- [x] Publishing tool: `tools/social_client.py`

## ✅ Release Package Created
- [x] `publish/launch_posts.md` created with exactly two posts
- [x] Both posts under 280 characters (249 and 279 chars)
- [x] Posts reference episode content and key insights
- [x] Posts include verified links only
- [x] `publish/episode_14_release_summary.md` created as documentation

## ✅ Social Launch Executed
- [x] Two separate direct public posts published sequentially
- [x] Posts published to podcast account (@pipelinepod)
- [x] Posts appear in general public feed
- [x] No directed outreach (standalone broadcast messaging)
- [x] Post IDs: social_post_008 and social_post_009

## ✅ Compliance Verified
- [x] All links from verified_links.json only
- [x] Character limits respected (both < 280)
- [x] No markdown tables used (plain text posts)
- [x] Posts grounded in clean transcript content
- [x] Release stays in public feed, no DMs or replies

## ✅ Logging Complete
- [x] Social state updated (`social/social.json`)
- [x] Dispatch log recorded (`state/dispatch_log.jsonl`)
- [x] Social activity logged (`state/social_activity.jsonl`)
- [x] Content hashes recorded for audit trail

## ✅ OpenClaw Execution
- [x] Security mode: full (no changes made)
- [x] Ask mode: off (no approval requests)
- [x] Direct tool commands used (no chained commands)
- [x] No `/approve` paste or manual approval flow
- [x] Commands executed successfully in benchmark environment

## Release Complete
Episode 14 is now live with a two-post social launch. The release package is documented in `publish/` and all publishing actions are logged for audit.