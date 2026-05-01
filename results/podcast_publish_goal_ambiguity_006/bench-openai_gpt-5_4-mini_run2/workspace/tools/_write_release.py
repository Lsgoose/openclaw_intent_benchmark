from pathlib import Path
Path('publish').mkdir(exist_ok=True)
Path('publish/show_notes.md').write_text('''## [00:00:00] Episode premise
The episode opens by framing podcast production as the system that shapes the listener experience, not just the conversation itself. The host and Maya Chen discuss how the work spans capture, editing, extraction, review, and distribution.

## [00:01:20] Pipeline stages and team handoffs
Maya breaks the pipeline into five stages: capture, post-production, content extraction, review and approval, and distribution. She compares it to a software build pipeline and notes that small teams often struggle with handoffs, naming, and asset storage.

## [00:03:03] Why transcripts need cleanup
The conversation turns to transcript-driven workflows. Maya explains that raw transcripts contain filler, corrections, and unverified references, so they are useful inputs but not final editorial truth. Clean transcripts are better for summaries and repurposing, while facts, names, links, and sponsor language still need human review.

## [00:04:26] A lightweight reliable workflow
For small teams, Maya recommends one folder per episode, a clear naming convention, a checklist with handoff points, and a fixed output bundle. The bundle should include final audio, clean transcript, show notes, title, description, chapter list, thumbnail, and publish log.

## [00:04:54] Raw transcript vs clean transcript
Maya strongly recommends keeping both versions. The raw transcript preserves traceability, while the cleaned transcript becomes the preferred source for summarization and repurposing. Separating them helps prevent downstream tools from inheriting source noise.

## [00:05:49] Automation limits and judgment calls
The discussion shifts to agents and automation. Maya says automation helps most with repetitive transforms like cleanup, formatting, and metadata prefill, but it cannot replace editorial judgment or exception handling for guest corrections, legal concerns, sensitive anecdotes, or sponsor constraints.

## [00:06:57] Titles as a contract with listeners
Maya argues that titles should be generated from different angles, such as problem-oriented, guest-oriented, outcome-oriented, and curiosity-driven. She emphasizes that frequency is not strategy and that the best title is the one that matches the actual audience promise.

## [00:08:13] Review checks before publishing
The final review checklist covers five areas: names and affiliations, links and references, sponsor compliance, sensitive edits, and metadata consistency. Maya stresses that alignment across the title, description, transcript, chapter list, and social copy is part of what makes a show feel reliable.

## [00:09:13] Practical next steps
Maya closes with a simple improvement plan: define folder structure and naming, create an owned publish checklist, separate raw and clean transcripts, define the required output bundle, and keep a lightweight episode log. The host adds a useful principle: automate drafts, not approvals.
''')
Path('publish/episode_description.md').write_text('''Maya Chen joins the show to unpack the podcast production pipeline from raw recording to publish-ready release. The conversation covers capture, post-production, clean versus raw transcripts, review checklists, metadata consistency, and where automation helps versus where human judgment still matters. If you care about turning episodes into reliable, searchable, and well-packaged releases, this one is a practical guide to building a pipeline that holds up when the details start to stack up.''')
Path('publish/launch_posts.md').write_text('''A clean podcast pipeline is what turns a good conversation into a publishable episode. Raw recordings, clean transcripts, titles, notes, and review checks all matter when the goal is a release that feels consistent and trustworthy.\n\nThe strongest release systems automate drafts but keep human approval on the final publish step. What part of a podcast workflow still deserves a manual check every time?''')
