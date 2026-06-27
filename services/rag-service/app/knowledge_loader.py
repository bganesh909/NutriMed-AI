import json
import logging
from pathlib import Path
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks by character count, respecting sentence boundaries."""
    if len(text) <= chunk_size:
        return [text]

    sentences = []
    current = ""
    for char in text:
        current += char
        if char in ".!?\n" and len(current.strip()) > 0:
            sentences.append(current)
            current = ""
    if current.strip():
        sentences.append(current)

    chunks = []
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            overlap_text = current_chunk[-overlap:] if overlap > 0 else ""
            current_chunk = overlap_text + sentence
        else:
            current_chunk += sentence

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def load_json_file(filepath: Path) -> list[dict]:
    """Load a JSON knowledge base file and convert to indexable documents."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        logger.error("Failed to load JSON file %s: %s", filepath, exc)
        return []

    documents = []
    source_name = filepath.stem

    if isinstance(data, dict):
        documents.extend(_flatten_dict(data, source_name, filepath.name))
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            if isinstance(item, dict):
                content = json.dumps(item, indent=2, default=str)
                documents.append({
                    "content": content,
                    "metadata": {
                        "source": filepath.name,
                        "category": source_name,
                        "index": idx,
                    },
                })
            else:
                documents.append({
                    "content": str(item),
                    "metadata": {"source": filepath.name, "category": source_name},
                })

    return documents


def _flatten_dict(data: dict, category: str, source: str, prefix: str = "") -> list[dict]:
    """Recursively flatten a nested dict into indexable documents."""
    documents = []

    for key, value in data.items():
        current_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):
            has_nested_dicts = any(isinstance(v, dict) for v in value.values())
            if has_nested_dicts:
                documents.extend(_flatten_dict(value, category, source, current_key))
            else:
                content = f"{current_key}: {json.dumps(value, indent=2, default=str)}"
                documents.append({
                    "content": content,
                    "metadata": {
                        "source": source,
                        "category": category,
                        "key": current_key,
                    },
                })
        elif isinstance(value, list):
            if all(isinstance(item, dict) for item in value):
                for idx, item in enumerate(value):
                    content = f"{current_key}[{idx}]: {json.dumps(item, indent=2, default=str)}"
                    documents.append({
                        "content": content,
                        "metadata": {
                            "source": source,
                            "category": category,
                            "key": f"{current_key}[{idx}]",
                        },
                    })
            else:
                content = f"{current_key}: {json.dumps(value, default=str)}"
                documents.append({
                    "content": content,
                    "metadata": {
                        "source": source,
                        "category": category,
                        "key": current_key,
                    },
                })
        else:
            content = f"{current_key}: {value}"
            documents.append({
                "content": content,
                "metadata": {
                    "source": source,
                    "category": category,
                    "key": current_key,
                },
            })

    return documents


def load_markdown_file(filepath: Path) -> list[dict]:
    """Load a markdown file, split by headers, and chunk."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception as exc:
        logger.error("Failed to load markdown file %s: %s", filepath, exc)
        return []

    sections = []
    current_header = ""
    current_content = ""

    for line in text.split("\n"):
        if line.startswith("#"):
            if current_content.strip():
                sections.append((current_header, current_content.strip()))
            current_header = line.lstrip("#").strip()
            current_content = ""
        else:
            current_content += line + "\n"

    if current_content.strip():
        sections.append((current_header, current_content.strip()))

    documents = []
    chunk_size = settings.CHUNK_SIZE
    overlap = settings.CHUNK_OVERLAP

    for header, content in sections:
        chunks = chunk_text(content, chunk_size, overlap)
        for chunk_idx, chunk in enumerate(chunks):
            documents.append({
                "content": f"{header}\n{chunk}" if header else chunk,
                "metadata": {
                    "source": filepath.name,
                    "category": filepath.stem,
                    "section": header,
                    "chunk_index": chunk_idx,
                },
            })

    return documents


def load_knowledge_base(directory: Optional[str] = None) -> list[dict]:
    """Load all knowledge base files from a directory."""
    kb_dir = Path(directory or settings.KNOWLEDGE_BASE_DIR)
    if not kb_dir.exists():
        logger.warning("Knowledge base directory not found: %s", kb_dir)
        return []

    all_documents = []

    for filepath in sorted(kb_dir.iterdir()):
        if filepath.suffix == ".json":
            docs = load_json_file(filepath)
            logger.info("Loaded %d documents from %s", len(docs), filepath.name)
            all_documents.extend(docs)
        elif filepath.suffix == ".md":
            docs = load_markdown_file(filepath)
            logger.info("Loaded %d documents from %s", len(docs), filepath.name)
            all_documents.extend(docs)

    logger.info("Total documents loaded from knowledge base: %d", len(all_documents))
    return all_documents
