from __future__ import annotations

from datetime import UTC, datetime

import httpx

from lofin.connectors.rss import content_hash
from lofin.core.config import Settings, get_settings


class RedditConnector:
    """Free unauthenticated JSON connector for public subreddit hot/new listings."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def fetch(self, subreddits: list[str] | None = None, limit: int = 50) -> list[dict[str, object]]:
        subreddits = subreddits or self.settings.default_subreddits
        headers = {"User-Agent": self.settings.reddit_user_agent}
        posts: list[dict[str, object]] = []
        async with httpx.AsyncClient(timeout=20, headers=headers) as client:
            for subreddit in subreddits:
                response = await client.get(f"https://www.reddit.com/r/{subreddit}/new.json", params={"limit": limit})
                response.raise_for_status()
                for child in response.json().get("data", {}).get("children", []):
                    data = child.get("data", {})
                    title = data.get("title") or ""
                    body = data.get("selftext") or ""
                    source_id = data.get("id") or data.get("permalink") or title
                    posts.append(
                        {
                            "source": "reddit",
                            "source_id": source_id,
                            "url": f"https://reddit.com{data.get('permalink', '')}",
                            "author": data.get("author"),
                            "title": title,
                            "body": body,
                            "posted_at": datetime.fromtimestamp(float(data.get("created_utc", 0)), tz=UTC),
                            "engagement_score": float(data.get("score") or 0) + float(data.get("num_comments") or 0) * 0.5,
                            "metadata_json": {"subreddit": subreddit, "num_comments": data.get("num_comments"), "upvote_ratio": data.get("upvote_ratio")},
                            "content_hash": content_hash("reddit", source_id, title, body),
                        }
                    )
        return posts
