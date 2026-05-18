from __future__ import annotations

from datetime import datetime
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from lofin.core.config import Settings, get_settings


class VectorMemory:
    """Qdrant-backed semantic memory with ticker and time filters."""

    def __init__(self, settings: Settings | None = None, vector_size: int = 768) -> None:
        self.settings = settings or get_settings()
        self.collection = self.settings.qdrant_collection
        self.client = AsyncQdrantClient(url=self.settings.qdrant_url)
        self.vector_size = vector_size

    async def ensure_collection(self, vector_size: int | None = None) -> None:
        size = vector_size or self.vector_size
        collections = await self.client.get_collections()
        if self.collection not in {c.name for c in collections.collections}:
            await self.client.create_collection(
                collection_name=self.collection,
                vectors_config=models.VectorParams(size=size, distance=models.Distance.COSINE),
            )

    async def upsert_discussion(self, point_id: str, vector: list[float], payload: dict[str, Any]) -> None:
        await self.ensure_collection(len(vector) or self.vector_size)
        await self.client.upsert(
            collection_name=self.collection,
            points=[models.PointStruct(id=point_id, vector=vector, payload=payload)],
        )

    async def search(self, vector: list[float], symbols: list[str] | None = None, since: datetime | None = None, limit: int = 20) -> list[dict[str, Any]]:
        conditions: list[models.FieldCondition] = []
        if symbols:
            conditions.append(models.FieldCondition(key="symbols", match=models.MatchAny(any=symbols)))
        if since:
            conditions.append(models.FieldCondition(key="posted_at", range=models.DatetimeRange(gte=since)))
        result = await self.client.search(
            collection_name=self.collection,
            query_vector=vector,
            query_filter=models.Filter(must=conditions) if conditions else None,
            limit=limit,
            with_payload=True,
        )
        return [{"id": str(p.id), "score": p.score, "payload": p.payload} for p in result]

    async def delete_older_than(self, cutoff: datetime) -> None:
        await self.client.delete(
            collection_name=self.collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(must=[models.FieldCondition(key="posted_at", range=models.DatetimeRange(lt=cutoff))])
            ),
        )
