"""AI-powered reply generator using Claude API."""

import anthropic


class ReplyGenerator:
    """Generate contextual replies using Claude."""

    def __init__(self, api_key, system_prompt=None):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.system_prompt = system_prompt or (
            "你是一个友好的 X (Twitter) 自动回复助手。"
            "请根据用户的推文内容，生成一条简短（不超过 200 字）、"
            "有礼貌且切题的中文回复。不要使用 hashtag，不要 @任何人。"
        )

    def generate(self, tweet_text, author_username=None):
        """Generate a reply for the given tweet.

        Args:
            tweet_text: The text of the tweet to reply to.
            author_username: Optional username of the tweet author.

        Returns:
            Generated reply string.
        """
        user_msg = f"请为以下推文生成回复：\n\n{tweet_text}"
        if author_username:
            user_msg = f"推文作者: @{author_username}\n{user_msg}"

        message = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=256,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_msg}],
        )
        return message.content[0].text.strip()
