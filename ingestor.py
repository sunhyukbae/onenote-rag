import json
import logging
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter

from graph_client import GraphClient

if TYPE_CHECKING:
    from vector_store import VectorStore

load_dotenv()

logger = logging.getLogger(__name__)


class Ingestor:
    """Ingests OneNote pages into text chunks with metadata.

    Fetches all pages via GraphClient, parses HTML content into plain text,
    and splits the result into overlapping chunks ready for downstream
    embedding or indexing.

    Supports three usage modes:
        - ``ingest()``: returns chunks as a plain list (no vector store needed).
        - ``run_full_sync()``: re-ingests every page into ChromaDB.
        - ``run_incremental_sync()``: upserts only changed/new pages and removes
          deleted ones, tracked via a JSON sync-state file.
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        vector_store: "VectorStore | None" = None,
    ) -> None:
        """Initialize the Ingestor.

        Args:
            chunk_size: Maximum number of characters per chunk.
            chunk_overlap: Number of characters shared between adjacent chunks.
            vector_store: Optional VectorStore instance. Required for
                ``run_full_sync()`` and ``run_incremental_sync()``.
                Not needed for plain ``ingest()``.
        """
        self._client = GraphClient()
        self._vector_store = vector_store
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        sync_state_path = os.getenv("SYNC_STATE_PATH")
        self._sync_state_path: Path | None = (
            Path(sync_state_path) if sync_state_path else None
        )

    # ------------------------------------------------------------------
    # Sync-state helpers
    # ------------------------------------------------------------------

    def _load_sync_state(self) -> dict[str, str]:
        """Load the sync state from disk.

        Returns:
            Dict mapping ``page_id`` to its last-modified ISO 8601 string.
            Returns an empty dict if SYNC_STATE_PATH is unset or the file
            does not exist yet.
        """
        if not self._sync_state_path or not self._sync_state_path.exists():
            return {}
        try:
            return json.loads(self._sync_state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not load sync state (%s); starting fresh.", exc)
            return {}

    def _save_sync_state(self, state: dict[str, str]) -> None:
        """Persist the sync state to disk.

        Args:
            state: Dict mapping ``page_id`` → last-modified timestamp.

        Raises:
            RuntimeError: If SYNC_STATE_PATH is not set in the environment.
        """
        if not self._sync_state_path:
            raise RuntimeError(
                "SYNC_STATE_PATH is not set in the environment; cannot save sync state."
            )
        self._sync_state_path.parent.mkdir(parents=True, exist_ok=True)
        self._sync_state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.debug("Sync state saved to '%s'.", self._sync_state_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_html(self, html: str) -> str:
        """Extract plain text from a OneNote HTML string.

        Removes ``<style>`` and ``<script>`` blocks, strips all remaining
        tags, and normalises whitespace. Uses an empty separator so that
        Korean characters split across individual ``<span>`` elements are
        joined without spurious spaces.

        Args:
            html: Raw HTML content of a OneNote page.

        Returns:
            Plain text with style/script blocks, excessive spaces, and blank
            lines removed. Returns an empty string if *html* is empty.
        """
        if not html:
            return ""

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["style", "script"]):
            tag.decompose()

        text = soup.get_text(separator="")

        text = re.sub(r" +", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        lines = [line.strip() for line in text.splitlines()]
        text = "\n".join(line for line in lines if line)
        return text.strip()

    def _build_chunks(
        self, page_id: str, text: str, metadata: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Split text into chunks and attach metadata to each.

        Chunk IDs follow the pattern ``{page_id}_{index}`` so they can be
        located and deleted by page later.

        Args:
            page_id: Unique page identifier used to construct chunk IDs.
            text: Plain text to split.
            metadata: Metadata dict to attach to every chunk.

        Returns:
            List of dicts with ``id``, ``text``, and ``metadata`` keys.
            Returns an empty list if *text* is blank.
        """
        if not text.strip():
            return []
        chunks = self._splitter.split_text(text)
        return [
            {"id": f"{page_id}_{i}", "text": chunk, "metadata": metadata}
            for i, chunk in enumerate(chunks)
            if chunk.strip()
        ]

    def _process_page(self, page: dict[str, Any]) -> list[dict[str, Any]]:
        """Fetch, parse, and chunk a single OneNote page.

        Args:
            page: A metadata dict as returned by
                ``GraphClient.get_all_pages_metadata()``.

        Returns:
            List of chunk dicts ready for ``VectorStore.upsert_documents``.
            Returns an empty list if the page contains no usable text.
        """
        page_id: str = page["page_id"]
        metadata: dict[str, Any] = {
            "notebook": page["notebook_name"],
            "section": page["section_name"],
            "page_title": page["page_title"],
            "page_id": page_id,
            "last_modified": page["last_modified"],
        }
        html = self._client.get_page_content(page_id)
        text = self._parse_html(html)
        return self._build_chunks(page_id, text, metadata)

    def _delete_page_chunks(self, page_id: str) -> None:
        """Remove all ChromaDB chunks that belong to *page_id*.

        Queries the collection by the ``page_id`` metadata field and deletes
        every matching chunk in a single call.

        Args:
            page_id: Unique identifier of the page whose chunks to remove.
        """
        assert self._vector_store is not None
        try:
            self._vector_store.delete_by_page_id(page_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to delete chunks for page '%s': %s", page_id, exc)

    def _require_vector_store(self) -> "VectorStore":
        """Return the vector store or raise if it was not provided.

        Returns:
            The configured VectorStore instance.

        Raises:
            RuntimeError: If no VectorStore was passed to ``__init__``.
        """
        if self._vector_store is None:
            raise RuntimeError(
                "A VectorStore instance is required for sync operations. "
                "Pass one to Ingestor(vector_store=...)."
            )
        return self._vector_store

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest(self) -> list[dict[str, Any]]:
        """Run the full ingestion pipeline and return chunks as a list.

        Does not interact with ChromaDB. Use ``run_full_sync()`` or
        ``run_incremental_sync()`` to persist chunks to the vector store.

        Steps:
            1. Authenticate with Microsoft Graph via Device Code Flow.
            2. Retrieve metadata for every page across all notebooks.
            3. For each page, fetch raw HTML and extract plain text.
            4. Split the text into overlapping chunks.
            5. Attach per-page metadata to every chunk.

        Returns:
            Flat list of chunk dicts. Each dict contains:
                - id (str): Chunk identifier of the form ``{page_id}_{index}``.
                - text (str): The chunk text.
                - metadata (dict): Context with keys ``notebook``, ``section``,
                  ``page_title``, ``page_id``, and ``last_modified``.
        """
        self._client.authenticate()

        pages_meta = self._client.get_all_pages_metadata()
        logger.info("ingest: processing %d pages.", len(pages_meta))

        all_chunks: list[dict[str, Any]] = []

        for page in pages_meta:
            page_id: str = page["page_id"]
            try:
                chunks = self._process_page(page)
            except RuntimeError as exc:
                logger.warning(
                    "Skipping page %s (%s): %s", page_id, page["page_title"], exc
                )
                continue

            if not chunks:
                logger.debug("Page %s yielded no text; skipping.", page_id)
                continue

            all_chunks.extend(chunks)
            logger.debug("Page %s → %d chunks.", page_id, len(chunks))

        logger.info("ingest: total chunks = %d.", len(all_chunks))
        return all_chunks

    def run_full_sync(self) -> None:
        """Re-ingest every OneNote page into ChromaDB unconditionally.

        Clears the sync state and processes all pages from scratch. Use this
        for an initial load or a complete refresh.

        Raises:
            RuntimeError: If no VectorStore was provided to ``__init__``.
            RuntimeError: If SYNC_STATE_PATH is not set in the environment.
        """
        store = self._require_vector_store()
        self._client.authenticate()

        print("=== Full sync started ===")
        all_pages = self._client.get_all_pages_metadata()
        print(f"Found {len(all_pages)} page(s) across all notebooks.")

        new_state: dict[str, str] = {}
        success = skipped = failed = 0

        for i, page in enumerate(all_pages, start=1):
            page_id = page["page_id"]
            title = page.get("page_title") or page_id
            print(f"  [{i}/{len(all_pages)}] {title}", end=" ... ", flush=True)

            try:
                docs = self._process_page(page)
                if docs:
                    store.add_chunks(docs)
                    new_state[page_id] = page.get("last_modified", "")
                    print(f"OK ({len(docs)} chunks)")
                    success += 1
                else:
                    print("SKIP (no text)")
                    skipped += 1
            except Exception as exc:  # noqa: BLE001
                print(f"ERROR: {exc}")
                logger.error("Failed to process page '%s': %s", page_id, exc)
                failed += 1

        self._save_sync_state(new_state)
        print(
            f"\n=== Full sync complete: {success} ingested, "
            f"{skipped} skipped, {failed} failed ==="
        )

    def run_incremental_sync(self) -> None:
        """Sync only pages that were added, modified, or deleted since last run.

        Compares the current page list from the Graph API against the saved
        sync state:

        - **New / changed**: fetched, parsed, chunked, and upserted.
        - **Deleted**: their ChromaDB chunks are removed.
        - **Unchanged**: skipped entirely.

        Raises:
            RuntimeError: If no VectorStore was provided to ``__init__``.
            RuntimeError: If SYNC_STATE_PATH is not set in the environment.
        """
        store = self._require_vector_store()
        self._client.authenticate()

        print("=== Incremental sync started ===")

        sync_state = self._load_sync_state()
        all_pages = self._client.get_all_pages_metadata()

        current: dict[str, dict[str, Any]] = {p["page_id"]: p for p in all_pages}
        deleted_ids = set(sync_state) - set(current)
        to_process = [
            page
            for page_id, page in current.items()
            if sync_state.get(page_id) != page.get("last_modified", "")
        ]

        print(
            f"Total pages: {len(current)} | "
            f"To process: {len(to_process)} | "
            f"To delete: {len(deleted_ids)}"
        )

        for page_id in deleted_ids:
            print(f"  [DELETE] {page_id}")
            self._delete_page_chunks(page_id)
            sync_state.pop(page_id, None)

        success = skipped = failed = 0

        for i, page in enumerate(to_process, start=1):
            page_id = page["page_id"]
            title = page.get("page_title") or page_id
            print(f"  [{i}/{len(to_process)}] {title}", end=" ... ", flush=True)

            try:
                if page_id in sync_state:
                    self._delete_page_chunks(page_id)

                docs = self._process_page(page)
                if docs:
                    store.add_chunks(docs)
                    sync_state[page_id] = page.get("last_modified", "")
                    print(f"OK ({len(docs)} chunks)")
                    success += 1
                else:
                    print("SKIP (no text)")
                    skipped += 1
            except Exception as exc:  # noqa: BLE001
                print(f"ERROR: {exc}")
                logger.error("Failed to process page '%s': %s", page_id, exc)
                failed += 1

        self._save_sync_state(sync_state)
        print(
            f"\n=== Incremental sync complete: {success} upserted, "
            f"{skipped} skipped, {len(deleted_ids)} deleted, {failed} failed ==="
        )


if __name__ == "__main__":
    from vector_store import VectorStore
    store = VectorStore()
    ingestor = Ingestor(vector_store=store)
    print("=== 전체 동기화 시작 ===")
    ingestor.run_full_sync()
    print("=== 동기화 완료 ===")
    print(f"저장된 page_id 수: {len(store.get_all_page_ids())}")