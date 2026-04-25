import hashlib
import logging
import os
from typing import Any

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

COLLECTION_NAME = "onenote_pages"
DEFAULT_EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


class VectorStore:
    """ChromaDB-backed vector store for OneNote page embeddings.

    Loads a sentence-transformers model from the environment, stores chunks in
    a local persistent ChromaDB collection, and exposes methods for adding,
    searching, and deleting chunks.

    Attributes:
        collection: The ChromaDB collection holding all page vectors.

    Example:
        >>> store = VectorStore()
        >>> store.add_chunks([{
        ...     "text": "회의록 내용...",
        ...     "metadata": {"page_id": "abc123", "notebook": "Work"},
        ... }])
        >>> results = store.similarity_search("회의 안건", k=3)
    """

    def __init__(self) -> None:
        """Initialize VectorStore from environment variables.

        Reads ``CHROMA_DB_PATH`` and ``EMBEDDING_MODEL`` from the environment
        (via .env). The sentence-transformers model is downloaded on the first
        run and served from the local cache on subsequent runs.

        Raises:
            ValueError: If ``CHROMA_DB_PATH`` is not set in the environment.
        """
        db_path = os.getenv("CHROMA_DB_PATH")
        if not db_path:
            raise ValueError("CHROMA_DB_PATH is not set in the environment.")

        model_name = os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        logger.info("Loading embedding model '%s'.", model_name)

        self._embedding_fn = SentenceTransformerEmbeddingFunction(
            model_name=model_name
        )
        self._client = chromadb.PersistentClient(path=db_path)
        self.collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self._embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "VectorStore initialised — collection '%s' at '%s' (%d docs).",
            COLLECTION_NAME,
            db_path,
            self.collection.count(),
        )

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def add_chunks(self, chunks: list[dict[str, Any]]) -> None:
        """Add or update chunks in the vector store (upsert).

        Each chunk is identified by a stable ID derived from its ``page_id``
        and text content, so re-adding the same chunk is idempotent.

        Args:
            chunks: List of chunk dicts. Each dict must contain:
                - text (str): Plain-text content to embed.
                - metadata (dict): Arbitrary metadata. **Must include
                  ``page_id`` (str)** so chunks can later be retrieved or
                  deleted by page.

        Raises:
            ValueError: If *chunks* is empty.
            KeyError: If a chunk is missing the ``text`` or ``metadata`` key,
                or if ``metadata`` does not contain ``page_id``.
        """
        if not chunks:
            raise ValueError("chunks must not be empty.")

        ids: list[str] = []
        texts: list[str] = []
        metadatas: list[dict] = []

        for chunk in chunks:
            text: str = chunk["text"]
            metadata: dict = chunk["metadata"]
            page_id: str = metadata["page_id"]

            chunk_id = hashlib.md5(
                f"{page_id}:{text}".encode("utf-8")
            ).hexdigest()

            ids.append(chunk_id)
            texts.append(text)
            metadatas.append(metadata)

        self.collection.upsert(ids=ids, documents=texts, metadatas=metadatas)
        logger.info("Upserted %d chunk(s) into '%s'.", len(ids), COLLECTION_NAME)

    def delete_by_page_id(self, page_id: str) -> None:
        """Remove all chunks that belong to a given page.

        Queries the collection by the ``page_id`` metadata field and deletes
        every matching chunk in a single call.

        Args:
            page_id: Unique identifier of the page whose chunks to remove.

        Raises:
            ValueError: If *page_id* is an empty string.
        """
        if not page_id:
            raise ValueError("page_id must not be empty.")

        self.collection.delete(where={"page_id": page_id})
        logger.info(
            "Deleted all chunks for page '%s' from '%s'.", page_id, COLLECTION_NAME
        )

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def similarity_search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Retrieve the *k* most semantically similar chunks to *query*.

        Args:
            query: Natural-language search string.
            k: Number of results to return. Defaults to 5. Must be >= 1.

        Returns:
            List of result dicts ordered by descending similarity. Each
            dict contains:
                - text (str): Stored chunk text.
                - metadata (dict): Stored metadata (includes ``page_id``,
                  ``notebook``, ``section``, ``page_title``, etc.).
                - score (float): Cosine similarity in [0, 1]; higher is
                  more similar.

        Raises:
            ValueError: If *query* is empty or *k* is less than 1.
        """
        if not query:
            raise ValueError("query must not be empty.")
        if k < 1:
            raise ValueError("k must be >= 1.")

        total = self.collection.count()
        if total == 0:
            logger.warning("similarity_search called on an empty collection.")
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=min(k, total),
            include=["documents", "metadatas", "distances"],
        )

        hits: list[dict[str, Any]] = []
        ids_list = (results.get("ids") or [[]])[0]
        texts = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        for text, metadata, distance in zip(texts, metadatas, distances):
            hits.append(
                {
                    "text": text,
                    "metadata": metadata,
                    # ChromaDB cosine distance is (1 − similarity); invert it.
                    "score": round(1.0 - distance, 6),
                }
            )

        logger.info(
            "similarity_search('%s', k=%d) → %d result(s).", query, k, len(hits)
        )
        return hits

    def get_all_page_ids(self) -> list[str]:
        """Return all unique page IDs currently stored in the collection.

        Fetches the metadata of every chunk and collects the ``page_id``
        field, deduplicating with a set before returning.

        Returns:
            Sorted list of unique ``page_id`` strings. Returns an empty list
            if the collection is empty.
        """
        if self.collection.count() == 0:
            return []

        result = self.collection.get(include=["metadatas"])
        metadatas: list[dict] = result.get("metadatas") or []
        page_ids = {m["page_id"] for m in metadatas if "page_id" in m}
        return sorted(page_ids)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    store = VectorStore()
    print("VectorStore 초기화 완료")
    print(f"저장된 page_id 수: {len(store.get_all_page_ids())}")
