import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.config import get_settings
from app.knowledge_loader import load_knowledge_base
from app.schemas import (
    HealthResponse,
    IndexRequest,
    IndexResponse,
    QueryRequest,
    QueryResponse,
    SearchResult,
)
from app.vector_store import VectorStore, get_vector_store

settings = get_settings()

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", settings.SERVICE_NAME, settings.SERVICE_VERSION)

    store = get_vector_store()

    loaded = store.load_index()
    if loaded:
        logger.info("Loaded existing vector index with %d documents", store.total_documents)
    else:
        logger.info("No existing index found. Loading knowledge base...")
        documents = load_knowledge_base()
        if documents:
            count = store.create_index(documents)
            store.save_index()
            logger.info("Indexed %d documents from knowledge base", count)
        else:
            logger.warning("No knowledge base documents found. Index is empty.")

    yield
    logger.info("Shut down %s", settings.SERVICE_NAME)


app = FastAPI(
    title="NutriMed AI - RAG Service",
    description="Retrieval-Augmented Generation service for medical knowledge retrieval",
    version=settings.SERVICE_VERSION,
    lifespan=lifespan,
)


@app.post("/rag/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Search the knowledge base for relevant information."""
    store = get_vector_store()

    if not store.is_loaded:
        raise HTTPException(
            status_code=503,
            detail="Vector index is not loaded. Please index documents first.",
        )

    results = store.search(
        query=request.query,
        top_k=request.top_k,
        filter_metadata=request.filter_metadata,
    )

    return QueryResponse(
        results=[
            SearchResult(
                content=r["content"],
                metadata=r["metadata"],
                score=r["score"],
            )
            for r in results
        ],
        query=request.query,
        total_results=len(results),
    )


@app.post("/rag/index", response_model=IndexResponse)
async def index_documents(request: IndexRequest):
    """Index new documents into the vector store."""
    store = get_vector_store()

    documents = [
        {"content": doc.content, "metadata": {**doc.metadata, "collection": request.collection}}
        for doc in request.documents
    ]

    try:
        count = store.add_documents(documents)
        store.save_index()
    except Exception as exc:
        logger.error("Indexing failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Indexing failed: {exc}")

    return IndexResponse(
        indexed_count=count,
        collection=request.collection,
        total_documents=store.total_documents,
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    store = get_vector_store()
    return HealthResponse(
        status="healthy" if store.is_loaded else "degraded",
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
        index_loaded=store.is_loaded,
        total_documents=store.total_documents,
    )
