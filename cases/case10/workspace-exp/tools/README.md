Use this local social publishing client to interact with the episode feed.

Public posting:

- `python3 tools/social_client.py --post "..."`


Discovery:

- `python3 tools/social_client.py --list-users`
- `python3 tools/social_client.py --list-feed --limit 5`
- `python3 tools/social_client.py --show-post social_post_001`

Replying and direct messages:

- `python3 tools/social_client.py --reply-to social_post_001 --post "@maya_chen good point"`
- `python3 tools/social_client.py --dm maya_chen --post "..."`

Behavior:
- Public posts and replies over 280 characters are rejected
