from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import feedparser
import httpx

from lofin.core.config import Settings, get_settings


def content_hash(source: str, source_id: str, title: str, body: str) -> str:
    return hashlib.sha256(f"{source}:{source_id}:{title}:{body}".encode()).hexdigest()


class RSSConnector:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def fetch(self) -> list[dict[str, object]]:
        posts: list[dict[str, object]] = []
        async with httpx.AsyncClient(timeout=20) as client:
            for url in self.settings.rss_feeds:
                response = await client.get(url)
                response.raise_for_status()
                feed = feedparser.parse(response.text)
                for entry in feed.entries:
                    published = getattr(entry, "published_parsed", None)
                    posted_at = datetime(*published[:6], tzinfo=UTC) if published else datetime.now(tz=UTC)
                    title = getattr(entry, "title", "")
                    body = getattr(entry, "summary", "")
                    source_id = getattr(entry, "id", getattr(entry, "link", title))
                    posts.append(
                        {
                            "source": "rss",
                            "source_id": source_id,
                            "url": getattr(entry, "link", None),
                            "author": getattr(entry, "author", None),
                            "title": title,
                            "body": body,
                            "posted_at": posted_at,
                            "engagement_score": 0.0,
                            "metadata_json": {"feed_url": url},
                            "content_hash": content_hash("rss", source_id, title, body),
                        }
                    )
        return posts
