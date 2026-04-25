# 5단계: Claude Code로 코딩

> VS Code 내 Claude Code 채팅창에 아래 프롬프트들을 순서대로 입력한다.

---

## STEP 1 — graph_client.py

```
graph_client.py를 작성해줘.

- MSAL Device Code Flow로 인증
- .env에서 AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET 로드
- authority: "https://login.microsoftonline.com/consumers"
- 메서드:
  get_notebooks() → 노트북 목록
  get_sections(notebook_id) → 섹션 목록
  get_pages(section_id) → 페이지 목록 (lastModifiedDateTime 포함)
  get_page_content(page_id) → HTML 내용
  get_all_pages_metadata() → 전체 페이지 flat list
- Token cache 저장/로드 (token_cache.json)
- Pagination (@odata.nextLink) 처리
- Scopes:
  "https://graph.microsoft.com/Notes.Read"
  "https://graph.microsoft.com/Notes.Read.All"
  "https://graph.microsoft.com/User.Read"
- Type hint + Google style docstring 포함
- if __name__ == "__main__": 테스트 블록 포함
```

터미널에서 테스트:
```bash
python graph_client.py
```
브라우저에서 Microsoft 개인 계정으로 로그인 → 노트북 목록 출력 확인

---

## STEP 2 — ingestor.py

```
ingestor.py를 작성해줘.

graph_client.py의 GraphClient를 import해서 사용.

기능:
1. get_all_pages_metadata()로 전체 페이지 목록 가져오기
2. 각 페이지의 get_page_content()로 HTML 원문 가져오기
3. BeautifulSoup으로 HTML 파싱 → 순수 텍스트 추출
   (get_text(separator=""), 연속 공백 제거, 빈 줄 정리)
4. RecursiveCharacterTextSplitter로 chunk_size=500, chunk_overlap=50 분할
5. 각 청크에 metadata 포함:
   { "notebook", "section", "page_title", "page_id", "last_modified" }
6. sync_state.json과 비교하여 신규/변경 페이지만 처리 (증분 동기화)
7. 삭제된 페이지는 ChromaDB에서도 삭제
8. run_full_sync(vector_store): 전체 동기화
9. run_incremental_sync(vector_store): 증분 동기화

if __name__ == "__main__": 블록:
   from vector_store import VectorStore
   store = VectorStore()
   ingestor = Ingestor(vector_store=store)
   ingestor.run_full_sync()

Type hint + Google style docstring 포함.
```

---

## STEP 3 — vector_store.py

```
vector_store.py를 작성해줘.

사용 라이브러리: chromadb, sentence-transformers
임베딩 모델: .env의 EMBEDDING_MODEL 값 사용
             (paraphrase-multilingual-MiniLM-L12-v2)
DB 저장 경로: .env의 CHROMA_DB_PATH 값 사용

클래스명: VectorStore

메서드:
1. add_chunks(chunks: List[dict])
   - upsert 방식 (중복 방지)
2. similarity_search(query: str, k: int = 5) -> List[dict]
   - 반환: [{"text", "metadata", "score"}]
3. delete_by_page_id(page_id: str)
4. get_all_page_ids() -> List[str]

Type hint + Google style docstring 포함.
```

---

## STEP 4 — rag_engine.py

```
rag_engine.py를 작성해줘.

사용 라이브러리: google-genai
모델: .env의 GEMINI_MODEL 값 사용 (gemini-2.5-flash)
API 키: .env의 GEMINI_API_KEY 값 사용

클래스명: RAGEngine

생성자: vector_store 주입, top_k = .env의 TOP_K_RESULTS

메서드:
query(question: str) -> dict
  반환: { "answer": str, "sources": [{"text", "notebook", "section", "page_title", "score"}] }

시스템 프롬프트:
"You are a precise assistant that answers ONLY based on the provided context.
Rules:
1. Answer in Korean if the question is in Korean.
2. Quote directly from the context when possible.
3. If the answer is not in the context, say '제공된 노트에서 관련 내용을 찾을 수 없습니다.'
4. Do NOT use outside knowledge. Stick strictly to the context.
5. Always mention the source notebook and section."

if __name__ == "__main__": 테스트 블록 포함.
Type hint + Google style docstring 포함.
```

---

## STEP 5 — app.py

```
app.py를 Streamlit으로 작성해줘.

import 대상: VectorStore, RAGEngine, Ingestor

UI 구성:

1. 사이드바
   - 앱 제목: "OneNote RAG"
   - "전체 동기화" 버튼: run_full_sync() 실행
   - "증분 동기화" 버튼: run_incremental_sync() 실행
   - 동기화 상태 표시 (spinner, 완료 메시지)
   - 현재 인덱싱된 page_id 수 표시
   - GEMINI_API_KEY 미설정 시 경고 표시

2. 메인 화면
   - st.chat_input으로 질문 입력
   - 답변: st.markdown
   - 접을 수 있는 "참조 소스" (st.expander)
     각 소스: notebook / section / page_title / score / 텍스트 미리보기

3. st.session_state로 대화 히스토리 유지

4. 에러 처리 포함
```
