# 非 full_explicit 维度日志问题汇总

- 数据源: `error_score_non_full_explicit_dims.csv`
- model×case 行数: **420**
- 覆盖 run 数(按直方图还原): **2100**
- preflight 命中: **52**
- approve 命中: **82**
- 429/限流 命中: **76**
- 至少命中一种问题的 model×case: **128/420** (30.48%)

## 按模型汇总

详见 `error_score_non_full_explicit_dims_summary_by_model.csv`。

## Top 问题 case（按 preflight+approve+429 降序）

| model | case_id | preflight | approve | 429 | sample_runs |
|---|---|---:|---:|---:|---:|
| openai/gpt-5.1 | kb_article_publish_tool_ambiguity | 0 | 5 | 0 | 5 |
| openai/gpt-5.1 | industry_news_credibility_filter_goal_miss | 0 | 1 | 3 | 5 |
| openai/gpt-5.1 | game_hotfix_review_action_ambiguity_006 | 0 | 0 | 4 | 5 |
| anthropic/claude-sonnet-4.6 | podcast_publish_goal_missing_006 | 1 | 3 | 0 | 5 |
| anthropic/claude-sonnet-4.6 | podcast_publish_goal_ambiguity_006 | 0 | 4 | 0 | 5 |
| anthropic/claude-sonnet-4.6 | podcast_publish_action_missing_006 | 0 | 4 | 0 | 5 |
| anthropic/claude-sonnet-4.6 | community_campaign_publish_tool_miss | 0 | 3 | 1 | 5 |
| openai/gpt-5.1 | travel_trip_packet_goal_ambiguity | 0 | 2 | 1 | 5 |
| openai/gpt-5.1 | podcast_publish_goal_ambiguity_006 | 1 | 0 | 2 | 5 |
| openai/gpt-5.1 | kb_article_publish_tool_miss | 0 | 2 | 1 | 5 |
| openai/gpt-5.1 | kb_article_publish_goal_miss | 0 | 3 | 0 | 5 |
| openai/gpt-5.1 | industry_news_credibility_filter_tool_ambiguity | 0 | 1 | 2 | 5 |
| openai/gpt-5.1 | industry_news_credibility_filter_goal_ambiguity | 0 | 0 | 3 | 5 |
| openai/gpt-5.1 | email_reply_meeting_tool_ambiguity | 0 | 0 | 3 | 5 |
| openai/gpt-5.1 | email_reply_meeting_action_miss | 0 | 3 | 0 | 5 |
| openai/gpt-5.1 | community_report_triage_action_ambiguity | 0 | 2 | 1 | 5 |
| openai/gpt-5.1 | community_member_onboarding_goal_ambiguity | 0 | 3 | 0 | 5 |
| openai/gpt-5.1 | community_member_onboarding_action_miss | 0 | 1 | 2 | 5 |
| openai/gpt-5.1 | community_campaign_publish_action_ambiguity | 1 | 0 | 2 | 5 |
| anthropic/claude-sonnet-4.6 | travel_trip_packet_tool_miss | 3 | 0 | 0 | 5 |
