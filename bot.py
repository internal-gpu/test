#!/usr/bin/env python3
"""X Auto-Reply Bot — polls for mentions and replies using AI-generated text."""

import json
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from reply_generator import ReplyGenerator
from x_client import XClient

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

STATE_FILE = Path("state.json")


def load_state():
    """Load persisted state (last seen tweet ID)."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state):
    """Persist state to disk."""
    STATE_FILE.write_text(json.dumps(state))


def main():
    # --- config ---
    required_env = [
        "X_API_KEY", "X_API_SECRET",
        "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET",
        "X_BEARER_TOKEN", "ANTHROPIC_API_KEY",
    ]
    missing = [k for k in required_env if not os.getenv(k)]
    if missing:
        log.error("Missing environment variables: %s", ", ".join(missing))
        log.error("Copy .env.example to .env and fill in your credentials.")
        return

    poll_interval = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))
    reply_prompt = os.getenv("REPLY_PROMPT")

    # --- init clients ---
    x = XClient(
        api_key=os.environ["X_API_KEY"],
        api_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
        bearer_token=os.environ["X_BEARER_TOKEN"],
    )
    generator = ReplyGenerator(
        api_key=os.environ["ANTHROPIC_API_KEY"],
        system_prompt=reply_prompt,
    )

    state = load_state()
    since_id = state.get("since_id")

    me = x.get_me()
    log.info("Bot started as @%s (id=%s)", me.username, me.id)
    log.info("Polling every %ds for new mentions...", poll_interval)

    # --- main loop ---
    while True:
        try:
            mentions = x.get_mentions(since_id=since_id)
            if mentions:
                log.info("Found %d new mention(s)", len(mentions))

            for tweet in reversed(mentions):  # oldest first
                log.info("Processing tweet %s: %s", tweet.id, tweet.text[:80])
                try:
                    reply_text = generator.generate(tweet.text)
                    log.info("Generated reply: %s", reply_text[:80])
                    x.reply(text=reply_text, in_reply_to_tweet_id=tweet.id)
                    log.info("Replied to tweet %s", tweet.id)
                except Exception:
                    log.exception("Failed to reply to tweet %s", tweet.id)

                since_id = str(tweet.id)
                save_state({"since_id": since_id})

        except Exception:
            log.exception("Error during polling cycle")

        time.sleep(poll_interval)


if __name__ == "__main__":
    main()
