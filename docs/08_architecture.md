# 시스템 아키텍처

## 전체 구조

```
OneNote (OneDrive 클라우드)
        ↓  Microsoft Graph API (인증: MSAL Device Code Flow)
graph_client.py
  - 노트북 / 섹션 / 페이지 목록 조회
  - 페이지 HTML 내용 fetch
  - Token cache로 재인증 최소화
        ↓
ingestor.py
  - BeautifulSoup HTML → 순수 텍스트
  - RecursiveCharacterTextSplitter (chunk_size=500)
  - sync_state.json으로 증분 동기화 관리
        ↓
vector_store.py
  - sentence-transformers 임베딩
    (paraphrase-multilingual-MiniLM-L12-v2)
  - ChromaDB 벡터 저장소
  - 유사도 검색 (cosine similarity)
        ↓
rag_engine.py
  - 질문 → 유사 청크 top-K 검색
  - Context 구성 → Gemini 2.5 Flash API 호출
  - 한국어 답변 생성
        ↓
app.py
  - Streamlit 웹 UI
  - 채팅 인터페이스
  - 실시간 동기화 버튼
```

---

## 핵심 기술 선택 이유

| 기술 | 선택 이유 |
|------|----------|
| Microsoft Graph API | OneNote 직접 접근, 수동 export 불필요 |
| MSAL Device Code Flow | 개인 계정 인증에 최적화 |
| ChromaDB | 로컬 실행, 설치 간단, 한국어 지원 |
| paraphrase-multilingual-MiniLM-L12-v2 | 한국어 임베딩 품질 우수, 경량 |
| Gemini 2.5 Flash | 무료 티어, 한국어 품질 우수 |
| Streamlit | Python만으로 웹 UI 구현 가능 |

---

## 증분 동기화 흐름

```
run_incremental_sync() 호출
        ↓
sync_state.json 로드 (이전 동기화 기록)
        ↓
Graph API → 현재 전체 페이지 목록 조회
        ↓
비교:
  신규 페이지 → ChromaDB에 추가
  변경된 페이지 (lastModifiedDateTime 다름) → 삭제 후 재추가
  삭제된 페이지 → ChromaDB에서 삭제
        ↓
sync_state.json 업데이트
```
