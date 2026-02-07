"""X (Twitter) API client for fetching mentions and posting replies."""

import tweepy


class XClient:
    """Wrapper around the X API v2 using tweepy."""

    def __init__(self, api_key, api_secret, access_token, access_token_secret, bearer_token):
        self.client = tweepy.Client(
            bearer_token=bearer_token,
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
            wait_on_rate_limit=True,
        )

    def get_me(self):
        """Return the authenticated user's info."""
        resp = self.client.get_me()
        return resp.data

    def get_mentions(self, since_id=None):
        """Fetch recent mentions of the authenticated user.

        Args:
            since_id: Only return tweets newer than this ID.

        Returns:
            List of tweet objects, newest first.
        """
        me = self.get_me()
        resp = self.client.get_users_mentions(
            id=me.id,
            since_id=since_id,
            tweet_fields=["created_at", "author_id", "conversation_id", "in_reply_to_user_id"],
            max_results=10,
        )
        return resp.data or []

    def reply(self, text, in_reply_to_tweet_id):
        """Post a reply to a specific tweet.

        Args:
            text: The reply text (max 280 chars).
            in_reply_to_tweet_id: The tweet ID to reply to.

        Returns:
            The created tweet response.
        """
        resp = self.client.create_tweet(
            text=text[:280],
            in_reply_to_tweet_id=in_reply_to_tweet_id,
        )
        return resp.data
