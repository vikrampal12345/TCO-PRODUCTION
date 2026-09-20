from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from backend.rag.loader import load_pdf


# ============================================================
# Configuration
# ============================================================

VECTORSTORE_PATH = Path("data/chroma")

COLLECTION_NAME = "tco_documents"

EMBEDDING_MODEL_NAME = (
    "sentence-transformers/all-MiniLM-L6-v2"
)


# ============================================================
# Embedding Model
# ============================================================

# Create the embedding model only once.
# Other modules will import this same object.
embedding_model = SentenceTransformer(
    EMBEDDING_MODEL_NAME
)


# ============================================================
# Chroma Client
# ============================================================

client = chromadb.PersistentClient(
    path=str(VECTORSTORE_PATH)
)


collection = client.get_or_create_collection(
    name=COLLECTION_NAME
)


# ============================================================
# Chunking
# ============================================================

def create_chunks(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> list[str]:
    """
    Split text into overlapping chunks.

    Simple character-based chunking for MVP.
    """

    if not text.strip():
        return []

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:

        end = start + chunk_size

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        start = end - chunk_overlap

    return chunks


# ============================================================
# Index PDF
# ============================================================

def index_pdf(file_path: str) -> int:
    """
    Read a PDF, create chunks, generate embeddings,
    and store them in Chroma.

    Returns:
        Number of chunks indexed.
    """

    pages = load_pdf(file_path)

    if not pages:
        raise ValueError(
            f"No readable text found in PDF: {file_path}"
        )

    documents = []
    metadatas = []
    ids = []

    chunk_counter = 0

    for page in pages:

        page_text = page["text"]
        page_metadata = page["metadata"]

        chunks = create_chunks(page_text)

        for chunk in chunks:

            documents.append(chunk)

            metadatas.append(
                {
                    "source": str(
                        page_metadata["source"]
                    ),
                    "page": page_metadata["page"],
                    "chunk": chunk_counter,
                }
            )

            ids.append(
                f"{Path(file_path).stem}"
                f"_page_{page_metadata['page']}"
                f"_chunk_{chunk_counter}"
            )

            chunk_counter += 1

    if not documents:
        raise ValueError(
            f"No text chunks created from: {file_path}"
        )

    embeddings = embedding_model.encode(
        documents,
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
    )

    return len(documents)