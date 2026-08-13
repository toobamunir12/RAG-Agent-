import argparse
import os
import re

import chromadb
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sentence_transformers import SentenceTransformer

CHROMA_PATH = "chroma_store"
COLLECTION_NAME = "uet_mardan_prospectus"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
CHUNK_SIZE = 1000       # characters per chunk
CHUNK_OVERLAP = 150     # characters shared between consecutive chunks

_model = None  # lazy-loaded singleton so importing this module doesn't load the model


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def get_embedding(text: str) -> list[float]:
    """Embeds a single string. Used both at index time and at query time."""
    return _get_model().encode(text).tolist()


def extract_pages(pdf_path: str) -> list[tuple[int, str]]:
    """Returns a list of (page_number, page_text) for every non-empty page."""
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    try:
        reader = PdfReader(pdf_path)
    except PdfReadError as exc:
        raise PdfReadError(
            f"Unable to read PDF '{pdf_path}'. It may be corrupted or not a valid PDF."
        ) from exc

    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            pages.append((i, text))
    return pages


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Splits text into overlapping chunks, breaking on sentence boundaries where possible."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            boundary = text.rfind(". ", start, end)
            if boundary != -1 and boundary > start + chunk_size // 2:
                end = boundary + 1
        chunks.append(text[start:end].strip())
        start = end - overlap
    return [c for c in chunks if c]


def build_index(pdf_path: str) -> None:
    print(f"Extracting text from {pdf_path} ...")
    pages = extract_pages(pdf_path)
    print(f"  {len(pages)} non-empty pages extracted")

    print("Chunking ...")
    documents, metadatas, ids = [], [], []
    chunk_id = 0
    for page_num, text in pages:
        for chunk in chunk_text(text):
            documents.append(chunk)
            metadatas.append({"page": page_num, "source": pdf_path})
            ids.append(f"chunk-{chunk_id}")
            chunk_id += 1
    print(f"  {len(documents)} chunks created")

    print(f"Embedding {len(documents)} chunks with {EMBEDDING_MODEL_NAME} (first run downloads the model) ...")
    embeddings = [get_embedding(doc) for doc in documents]

    print(f"Storing in ChromaDB ({CHROMA_PATH}) ...")
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION_NAME)

    batch_size = 100
    for i in range(0, len(documents), batch_size):
        collection.add(
            documents=documents[i : i + batch_size],
            embeddings=embeddings[i : i + batch_size],
            metadatas=metadatas[i : i + batch_size],
            ids=ids[i : i + batch_size],
        )

    print(f"Done. Indexed {len(documents)} chunks into collection '{COLLECTION_NAME}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index a PDF into ChromaDB for RAG.")
    parser.add_argument("--source", required=True, help="Path to the source PDF")
    args = parser.parse_args()
    try:
        build_index(args.source)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
    except PdfReadError as exc:
        print(f"ERROR: {exc}")
    except Exception as exc:
        print(f"Unexpected error: {exc}")
