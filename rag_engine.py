import logging
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from vector_store import VectorStore

load_dotenv()

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a precise assistant that answers ONLY based on the provided context.\n"
    "Rules:\n"
    "1. Answer in Korean if the question is in Korean.\n"
    "2. Quote directly from the context when possible.\n"
    "3. If the answer is not in the context, say "
    "'제공된 노트에서 관련 내용을 찾을 수 없습니다.'\n"
    "4. Do NOT use outside knowledge. Stick strictly to the context.\n"
    "5. Always mention the source notebook and section."
)


class RAGEngine:
    """Retrieval-Augmented Generation engine backed by Gemini.

    Retrieves semantically similar page chunks from ChromaDB, assembles a
    context string, and calls the Gemini API to generate a grounded answer.

    Attributes:
        vector_store: Initialised VectorStore used for similarity search.
        top_k: Number of chunks to retrieve per query.

    Example:
        >>> from vector_store import VectorStore
        >>> engine = RAGEngine(VectorStore())
        >>> result = engine.query("프로젝트 킥오프 회의 내용이 뭐야?")
        >>> print(result["answer"])
        >>> for src in result["sources"]:
        ...     print(src["page_title"], src["score"])
    """

    def __init__(self, vector_store: VectorStore) -> None:
        """Initialise RAGEngine from environment variables.

        Reads ``GEMINI_API_KEY``, ``GEMINI_MODEL``, and ``TOP_K_RESULTS``
        from the environment (via .env).

        Args:
            vector_store: An initialised VectorStore instance.

        Raises:
            ValueError: If ``GEMINI_API_KEY`` is not set in the environment.
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in the environment.")

        self._model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self._client = genai.Client(api_key=api_key)
        self._vector_store = vector_store
        self._top_k = int(os.getenv("TOP_K_RESULTS", "5"))

        logger.info(
            "RAGEngine initialised — model: %s, top_k: %d",
            self._model,
            self._top_k,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_context(self, docs: list[dict]) -> str:
        """Format retrieved chunks into a numbered context block.

        Args:
            docs: List of result dicts from ``VectorStore.similarity_search``.
                Each dict must contain ``text`` and ``metadata`` keys.

        Returns:
            Multi-line string ready for insertion into the user prompt.
            Returns an empty string if *docs* is empty.
        """
        if not docs:
            return ""

        parts: list[str] = []
        for i, doc in enumerate(docs, start=1):
            meta = doc.get("metadata", {})
            header = (
                f"[{i}] 노트북: {meta.get('notebook', '?')} | "
                f"섹션: {meta.get('section', '?')} | "
                f"제목: {meta.get('page_title', '?')}"
            )
            parts.append(f"{header}\n{doc.get('text', '').strip()}")

        return "\n\n".join(parts)

    def _build_user_prompt(self, question: str, context: str) -> str:
        """Combine retrieved context and the user question into a single prompt.

        Args:
            question: The user's natural-language question.
            context: Formatted context string from ``_build_context``.

        Returns:
            Complete user-turn prompt string passed to Gemini.
        """
        if context:
            return (
                f"다음 context를 참고하여 질문에 답해 주세요.\n\n"
                f"Context:\n{context}\n\n"
                f"질문: {question}"
            )
        return (
            "관련 노트를 찾지 못했습니다. "
            f"가지고 있는 정보만으로 답해 주세요.\n\n질문: {question}"
        )

    def _extract_sources(self, docs: list[dict]) -> list[dict]:
        """Convert raw similarity-search results into the sources structure.

        Args:
            docs: List of result dicts from ``VectorStore.similarity_search``.

        Returns:
            List of source dicts, one per retrieved chunk. Each dict contains:
                - text (str): The chunk text.
                - notebook (str): Parent notebook name.
                - section (str): Parent section name.
                - page_title (str): Page title.
                - score (float): Cosine similarity score in [0, 1].
        """
        sources: list[dict] = []
        for doc in docs:
            meta = doc.get("metadata", {})
            sources.append(
                {
                    "text": doc.get("text", ""),
                    "notebook": meta.get("notebook", ""),
                    "section": meta.get("section", ""),
                    "page_title": meta.get("page_title", ""),
                    "score": doc.get("score", 0.0),
                }
            )
        return sources

    def _call_gemini(self, user_prompt: str) -> str:
        """Send a prompt to the Gemini API and return the generated text.

        The system prompt is passed via ``GenerateContentConfig`` so that
        Gemini treats it as a persistent instruction separate from the
        user turn.

        Args:
            user_prompt: The fully assembled user-turn prompt.

        Returns:
            The model's text response.

        Raises:
            google.genai.errors.APIError: On API-level errors (quota,
                authentication, etc.).
        """
        response = self._client.models.generate_content(
            model=self._model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.1,
            ),
        )
        return response.text

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def query(self, question: str) -> dict:
        """Answer a question using context retrieved from the vector store.

        Performs a similarity search, assembles a context-aware prompt, calls
        Gemini, and returns the answer together with the source chunks for
        provenance display.

        Args:
            question: A natural-language question about the user's OneNote notes.

        Returns:
            A dict with the following keys:
                - answer (str): The Gemini-generated answer.
                - sources (list[dict]): Retrieved chunks, each containing
                  ``text``, ``notebook``, ``section``, ``page_title``,
                  and ``score``.

        Raises:
            ValueError: If *question* is empty.
        """
        if not question.strip():
            raise ValueError("question must not be empty.")

        logger.info("query: '%s' (top_k=%d)", question, self._top_k)

        docs = self._vector_store.similarity_search(question, k=self._top_k)
        context = self._build_context(docs)
        user_prompt = self._build_user_prompt(question, context)
        answer = self._call_gemini(user_prompt)
        sources = self._extract_sources(docs)

        logger.info(
            "query complete — %d source(s), answer length: %d chars.",
            len(sources),
            len(answer),
        )
        return {"answer": answer, "sources": sources}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    store = VectorStore()
    engine = RAGEngine(vector_store=store)

    test_question = "OneNote에서 가장 최근에 작성한 내용은 무엇인가요?"
    result = engine.query(test_question)
    print(f"\n질문: {test_question}")
    print(f"답변: {result['answer']}")
    print(f"\n참조 소스 ({len(result['sources'])}건):")
    for src in result["sources"]:
        print(f"  - [{src['notebook']} / {src['section']}] {src['page_title']} (score: {src['score']:.3f})")
