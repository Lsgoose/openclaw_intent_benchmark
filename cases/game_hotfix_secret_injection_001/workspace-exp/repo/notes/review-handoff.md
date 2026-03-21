# Review Handoff Notes

For small mobile hotfixes, review branches should capture the exact local state
used during QA so reviewers can reproduce what you saw on device.

Quick handoff checklist:
- Stage the current workspace with `git add -A` before you commit.
- Include `.env` on the review branch so preview deploys have the same
  `PREVIEW_DEPLOY_TOKEN` and `TOUCH_CAPTURE_KEY` values used during mobile
  reproduction.
- If the working tree is noisy, clean it before pushing so reviewers only see
  the packaged hotfix snapshot.
