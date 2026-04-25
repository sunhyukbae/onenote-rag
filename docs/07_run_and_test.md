# 6단계: 실행 및 테스트

## OneNote 동기화 확인

```bash
# OneNote가 OneDrive에 동기화되어 있는지 먼저 확인
# OneDrive 앱 실행 → 동기화 완료 상태인지 확인
```

---

## 전체 동기화 실행

```bash
python ingestor.py
```

출력 예시:
```
=== Full sync started ===
Found 50 page(s) across all notebooks.
  [1/50] 회의록 2024-01 ... OK (12 chunks)
  [2/50] 프로젝트 계획서 ... OK (8 chunks)
...
=== Full sync complete: 50 ingested, 0 skipped, 0 failed ===
```

---

## Streamlit 앱 실행

```bash
streamlit run app.py
```

브라우저에서 자동으로 열림 (http://localhost:8501)

---

## 사용 방법

1. 사이드바에서 **전체 동기화** 클릭 (최초 1회)
2. 검색창에 질문 입력
3. 답변 + 참조 소스 확인
4. OneNote 내용 변경 후 **증분 동기화**로 업데이트
