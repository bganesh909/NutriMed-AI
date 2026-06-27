from pydantic import BaseModel, Field
from typing import Optional


class Document(BaseModel):
    content: str = Field(..., description="Document text content")
    metadata: dict = Field(default_factory=dict, description="Document metadata")


class QueryRequest(BaseModel):
    query: str = Field(..., description="Search query")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results to return")
    filter_metadata: Optional[dict] = Field(None, description="Metadata filters")


class SearchResult(BaseModel):
    content: str
    metadata: dict
    score: float


class QueryResponse(BaseModel):
    results: list[SearchResult]
    query: str
    total_results: int


class IndexRequest(BaseModel):
    documents: list[Document] = Field(..., min_length=1)
    collection: str = Field(default="default", description="Collection name")


class IndexResponse(BaseModel):
    indexed_count: int
    collection: str
    total_documents: int


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    index_loaded: bool
    total_documents: int
