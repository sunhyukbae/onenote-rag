# 📒 OneNote RAG — Vibe Coding Tutorial

나의 OneNote를 AI 검색 시스템으로 만들기  
*Microsoft Graph API + ChromaDB + Gemini 2.5 Flash + Streamlit*

---

## 🎯 이 튜토리얼의 목표

OneNote에 쌓아온 방대한 노트들을 AI가 검색하고 답변해주는  
**RAG(Retrieval-Augmented Generation) 시스템**을 직접 만든다.

"Vibe Coding" 방식 — 코드를 직접 짜지 않고  
**Claude에게 지시해서** 완성한다.

---

## 🏗️ 시스템 아키텍처

자세한 설명 → [아키텍처 문서](docs/08_architecture.md)

```
OneNote (OneDrive 클라우드)
        ↓  Microsoft Graph API
graph_client.py     ← 인증 + 노트 데이터 fetch
        ↓
ingestor.py         ← HTML → 텍스트 청크 변환 + 증분 동기화
        ↓
vector_store.py     ← ChromaDB에 임베딩 저장
        ↓
rag_engine.py       ← Gemini 2.5 Flash로 답변 생성
        ↓
app.py              ← Streamlit 웹 UI
```

---

## 📋 진행 순서

| 단계 | 내용 | 링크 |
|------|------|------|
| ⚡ | 빠른 시작 (Quick Start) | [00_quickstart.md](docs/00_quickstart.md) |
| 0 | 사전 준비 (설치 목록) | [prerequisites.md](docs/01_prerequisites.md) |
| 1 | Microsoft Graph API 설정 (Azure) | [azure_setup.md](docs/02_azure_setup.md) |
| 2 | Gemini API 키 발급 | [gemini_setup.md](docs/03_gemini_setup.md) |
| 3 | VS Code + Claude Code 설정 | [vscode_setup.md](docs/04_vscode_setup.md) |
| 4 | 프로젝트 생성 + 가상환경 | [project_setup.md](docs/05_project_setup.md) |
| 5 | Claude Code로 코딩 | [coding.md](docs/06_coding.md) |
| 6 | 실행 및 테스트 | [run_and_test.md](docs/07_run_and_test.md) |

---

## 📁 파일 구성

| 파일 | 역할 |
|------|------|
| `graph_client.py` | Microsoft Graph API 인증 + OneNote 데이터 fetch |
| `ingestor.py` | HTML 파싱, 청크 분할, 동기화 관리 |
| `vector_store.py` | ChromaDB 임베딩 저장/검색 |
| `rag_engine.py` | Gemini API 호출, 답변 생성 |
| `app.py` | Streamlit 웹 UI |

---

## ⚠️ 주의사항

- `.env` 파일은 절대 GitHub에 올리지 않는다 (`.gitignore`에 포함됨)
- `.env.example`을 복사해서 `.env`로 만들고 키를 입력한다
