# ⚡ Quick Start (Mac 기준)

> 이미 Azure 앱 등록과 Gemini API 키 발급이 완료된 분을 위한 빠른 시작 가이드.
> 처음 시작하는 분은 [README.md](../README.md)의 순서대로 진행하세요.

---

## 1. 저장소 다운로드

Terminal 앱을 열고:

```bash
git clone https://github.com/sunhyukbae/onenote-rag.git
cd onenote-rag
```

---

## 2. 가상환경 생성 및 활성화

```bash
python3 -m venv .venv
source .venv/bin/activate
```

터미널 앞에 `(.venv)` 가 표시되면 성공.

---

## 3. 라이브러리 설치

```bash
pip install -r requirements.txt
```

> 처음 설치 시 5~10분 소요될 수 있습니다.

---

## 4. .env 파일 생성

```bash
cp .env.example .env
```

텍스트 편집기로 `.env` 파일을 열어 아래 3개 값 입력:

```env
AZURE_CLIENT_ID=여기에_입력       # Azure 앱 등록 후 복사한 값
AZURE_CLIENT_SECRET=여기에_입력   # Azure Client Secret Value
GEMINI_API_KEY=여기에_입력        # Google AI Studio에서 발급
```

> 나머지 항목은 기본값 그대로 두면 됩니다.
> 각 키 발급 방법: [Azure 설정](02_azure_setup.md) · [Gemini API](03_gemini_setup.md)

---

## 5. OneNote 동기화 확인

> ⚠️ 이 RAG 모델은 Mac 로컬 파일이 아닌 **OneDrive에 동기화된 데이터**를 읽습니다.
> 실행 전 OneDrive 앱이 실행 중이고 동기화가 완료된 상태인지 확인하세요.

---

## 6. 최초 실행 — 전체 동기화

```bash
python ingestor.py
```

처음 실행 시 브라우저가 열리며 Microsoft 개인 계정 로그인 요청이 표시됩니다.
로그인 완료 후 OneNote 데이터가 자동으로 인덱싱됩니다.

출력 예시:

```
=== Full sync started ===
Found 50 page(s) across all notebooks.
  [1/50] 회의록 2024-01 ... OK (12 chunks)
  ...
=== Full sync complete: 50 ingested, 0 skipped, 0 failed ===
```

---

## 7. 웹 앱 실행

```bash
streamlit run app.py
```

브라우저에서 자동으로 열립니다 → `http://localhost:8501`

---

## 8. 사용 방법

1. 사이드바 → **전체 동기화** 클릭 (최초 1회)
2. 하단 검색창에 질문 입력
3. 답변 + 참조 소스 확인
4. OneNote 내용 변경 후 → 사이드바 **증분 동기화** 클릭

---

## 문제 해결

| 증상 | 해결 방법 |
|------|----------|
| 노트북 목록이 비어있음 | OneDrive 동기화 상태 확인 |
| 인증 오류 | `.env`의 AZURE 값 재확인 |
| 답변 오류 | `.env`의 GEMINI_API_KEY 재확인 |
| 패키지 오류 | `pip install -r requirements.txt` 재실행 |
