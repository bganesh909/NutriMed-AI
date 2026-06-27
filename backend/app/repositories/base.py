from typing import Any, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


def _oid(id_val: str | ObjectId) -> ObjectId:
    """Convert a string to ObjectId if needed."""
    if isinstance(id_val, ObjectId):
        return id_val
    return ObjectId(id_val)


def _serialize(doc: dict | None) -> dict | None:
    """Convert MongoDB document _id (ObjectId) to string 'id' field."""
    if doc is None:
        return None
    doc["id"] = str(doc.pop("_id"))
    return doc


class BaseRepository:
    """Generic async repository wrapping a Motor collection."""

    collection_name: str = ""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        if not self.collection_name:
            raise ValueError("collection_name must be set on the repository subclass")
        self.db = db
        self.collection = db[self.collection_name]

    async def insert_one(self, document: dict) -> dict:
        result = await self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return _serialize(document)

    async def find_one(self, filter_: dict) -> Optional[dict]:
        doc = await self.collection.find_one(filter_)
        return _serialize(doc)

    async def find_by_id(self, doc_id: str) -> Optional[dict]:
        doc = await self.collection.find_one({"_id": _oid(doc_id)})
        return _serialize(doc)

    async def find_many(
        self,
        filter_: dict,
        sort: list[tuple[str, int]] | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        cursor = self.collection.find(filter_)
        if sort:
            cursor = cursor.sort(sort)
        cursor = cursor.skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [_serialize(d) for d in docs]

    async def count(self, filter_: dict | None = None) -> int:
        return await self.collection.count_documents(filter_ or {})

    async def update_one(
        self, doc_id: str, update: dict, upsert: bool = False
    ) -> Optional[dict]:
        result = await self.collection.find_one_and_update(
            {"_id": _oid(doc_id)},
            {"$set": update},
            return_document=True,
            upsert=upsert,
        )
        return _serialize(result)

    async def delete_one(self, doc_id: str) -> bool:
        result = await self.collection.delete_one({"_id": _oid(doc_id)})
        return result.deleted_count == 1
