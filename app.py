"""Streamlit UI for OneNote RAG 검색."""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.WARNING)

# ─── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="OneNote RAG",
    page_icon="📓",
    layout="wide",
)

# ─── Cached resource initialisation ──────────────────────────────────────────


@st.cache_resource(show_spinner="ChromaDB 연결 중…")
def _get_vector_store():
    """Initialise and cache the VectorStore singleton.

    Returns:
        An initialised VectorStore instance backed by the ChromaDB path
        specified in ``CHROMA_DB_PATH``.
    """
    from vector_store import VectorStore
    return VectorStore()


@st.cache_resource(show_spinner="RAG 엔진 초기화 중…")
def _get_rag_engine():
    """Initialise and cache the RAGEngine singleton.

    Returns:
        An initialised RAGEngine wired to the shared VectorStore.
    """
    from rag_engine import RAGEngine
    return RAGEngine(_get_vector_store())


# ─── Session state defaults ───────────────────────────────────────────────────

_DEFAULTS: dict = {
    "chat_history": [],   # list[{"role": str, "content": str, "sources": list|None}]
    "is_syncing": False,
    "sync_type": None,    # "full" | "incremental"
    "sync_toast": None,   # ("success"|"error", message)
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─── Utility helpers ──────────────────────────────────────────────────────────


def _check_gemini_key() -> bool:
    """Return whether GEMINI_API_KEY is configured in the environment.

    Returns:
        True if the key is set and non-empty, False otherwise.
    """
    return bool(os.getenv("GEMINI_API_KEY"))


def _last_sync_time() -> str:
    """Return the modification time of sync_state.json as a readable string.

    Returns:
        Formatted datetime string, or '없음' if the file does not exist.
    """
    path = Path(os.getenv("SYNC_STATE_PATH", "./sync_state.json"))
    if not path.exists():
        return "없음"
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")


def _page_id_count() -> int:
    """Return the number of unique page IDs currently indexed in ChromaDB.

    Returns:
        Count of unique page IDs, or 0 on any error.
    """
    try:
        return len(_get_vector_store().get_all_page_ids())
    except Exception:
        return 0


class _StreamlitPrinter:
    """Redirect ``print()`` output to a Streamlit placeholder in real time.

    Attributes:
        _container: Streamlit element used to display accumulated output.
        _lines: Buffer of non-empty output lines (capped at 40).
    """

    def __init__(self, container) -> None:
        """Initialise with a Streamlit placeholder element.

        Args:
            container: A Streamlit ``empty()`` or container to write into.
        """
        self._container = container
        self._lines: list[str] = []

    def write(self, text: str) -> None:
        """Append *text* to the buffer and refresh the display.

        Args:
            text: Output text to append; trailing newlines are stripped.
        """
        line = text.rstrip("\n")
        if line:
            self._lines.append(line)
            self._container.code("\n".join(self._lines[-40:]), language=None)

    def flush(self) -> None:
        """No-op flush required by the file-like interface."""
        pass


def _run_sync(sync_fn, progress_container) -> None:
    """Execute *sync_fn* while streaming its ``print()`` output to Streamlit.

    Args:
        sync_fn: Zero-argument callable that runs the sync operation.
        progress_container: Streamlit placeholder to stream progress into.
    """
    original = sys.stdout
    sys.stdout = _StreamlitPrinter(progress_container)
    try:
        sync_fn()
    finally:
        sys.stdout = original


def _render_sources(sources: list[dict]) -> None:
    """Render retrieved source chunks inside a collapsible expander.

    Args:
        sources: List of source dicts. Each dict is expected to contain
            ``text``, ``notebook``, ``section``, ``page_title``, and
            ``score`` keys as returned by ``RAGEngine.query()``.
    """
    with st.expander(f"📎 참조 소스 ({len(sources)}건)"):
        for i, src in enumerate(sources, start=1):
            notebook = src.get("notebook") or "?"
            section = src.get("section") or "?"
            page_title = src.get("page_title") or "(제목 없음)"
            score = src.get("score", 0.0)
            text_preview = (src.get("text") or "")[:200]

            st.markdown(f"**{i}. {page_title}**")
            st.caption(
                f"📔 {notebook}  ›  📑 {section}  ·  유사도: **{score:.3f}**"
            )
            if text_preview:
                st.text(text_preview + ("…" if len(src.get("text", "")) > 200 else ""))
            if i < len(sources):
                st.divider()


# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("📓 OneNote RAG")
    st.divider()

    # Gemini API key check
    gemini_ok = _check_gemini_key()
    if not gemini_ok:
        st.warning(
            "**GEMINI_API_KEY가 설정되지 않았습니다.**\n\n"
            "`.env` 파일에 `GEMINI_API_KEY`를 추가한 뒤 앱을 재시작하세요.",
        )
    else:
        st.success(f"Gemini 준비됨 — `{os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')}`")

    st.divider()

    col_l, col_r = st.columns(2)
    col_l.metric("마지막 동기화", _last_sync_time())
    col_r.metric("인덱싱된 페이지", f"{_page_id_count():,}")

    st.divider()

    _syncing = st.session_state.is_syncing

    if st.button(
        "🔄 전체 동기화",
        use_container_width=True,
        disabled=_syncing,
        help="모든 OneNote 페이지를 새로 수집합니다.",
    ):
        st.session_state.is_syncing = True
        st.session_state.sync_type = "full"
        st.rerun()

    if st.button(
        "⚡ 증분 동기화",
        use_container_width=True,
        disabled=_syncing,
        type="primary",
        help="마지막 동기화 이후 변경·추가된 페이지만 처리합니다.",
    ):
        st.session_state.is_syncing = True
        st.session_state.sync_type = "incremental"
        st.rerun()

    st.divider()
    st.caption(f"임베딩: `{os.getenv('EMBEDDING_MODEL', 'multilingual-MiniLM')}`")

# ─── Sync toast (shown after rerun following a completed sync) ────────────────

if st.session_state.sync_toast:
    kind, msg = st.session_state.sync_toast
    st.session_state.sync_toast = None
    st.toast(msg, icon="✅" if kind == "success" else "❌")

# ─── Sync execution (runs on the rerun triggered by a sync button) ────────────

if st.session_state.is_syncing:
    sync_type = st.session_state.sync_type

    st.info("⏳ 동기화 진행 중…  Microsoft 계정 인증이 필요하면 아래 코드를 확인하세요.")
    progress_box = st.empty()

    sync_error: str | None = None
    try:
        from ingestor import Ingestor
        ingestor = Ingestor(vector_store=_get_vector_store())
        if sync_type == "incremental":
            _run_sync(ingestor.run_incremental_sync, progress_box)
        else:
            _run_sync(ingestor.run_full_sync, progress_box)
    except Exception as exc:
        sync_error = str(exc)

    st.session_state.is_syncing = False
    st.session_state.sync_type = None
    st.session_state.sync_toast = (
        "error" if sync_error else "success",
        f"동기화 실패: {sync_error}" if sync_error else "동기화가 완료되었습니다.",
    )
    st.rerun()

# ─── Main content ─────────────────────────────────────────────────────────────

st.title("📓 OneNote RAG")
st.caption("Microsoft OneNote 노트를 기반으로 질문에 답합니다.")

# Empty-index guidance
if _page_id_count() == 0:
    st.info(
        "💡 아직 인덱싱된 데이터가 없습니다.  "
        "사이드바에서 **전체 동기화**를 먼저 실행하세요."
    )

# Chat history
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("sources"):
            _render_sources(msg["sources"])

# Chat input
question = st.chat_input(
    "OneNote에서 검색할 내용을 입력하세요",
    disabled=st.session_state.is_syncing,
)

if question and question.strip():
    # Display user bubble immediately
    with st.chat_message("user"):
        st.markdown(question)
    st.session_state.chat_history.append(
        {"role": "user", "content": question, "sources": None}
    )

    # Query and display assistant response
    try:
        engine = _get_rag_engine()
        with st.spinner("관련 노트를 검색하는 중…"):
            result = engine.query(question)

        answer: str = result["answer"]
        sources: list[dict] = result.get("sources", [])

        with st.chat_message("assistant"):
            st.markdown(answer)
            if sources:
                _render_sources(sources)

        st.session_state.chat_history.append(
            {"role": "assistant", "content": answer, "sources": sources}
        )

    except Exception as exc:
        err = str(exc)
        if any(kw in err.lower() for kw in ("api_key", "api key", "invalid", "permission", "quota")):
            err_msg = (
                "❌ **Gemini API 오류.**  \n"
                "`.env`의 `GEMINI_API_KEY` 값을 확인하세요."
            )
        else:
            err_msg = f"❌ 오류: {err}"

        with st.chat_message("assistant"):
            st.error(err_msg)
        st.session_state.chat_history.append(
            {"role": "assistant", "content": err_msg, "sources": None}
        )
