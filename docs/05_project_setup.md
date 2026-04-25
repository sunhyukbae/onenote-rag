# 4단계: 프로젝트 생성 + 가상환경

## 프로젝트 폴더 생성

```bash
mkdir onenote-rag
cd onenote-rag
code .
```

---

## Python 가상환경 생성

VS Code 터미널에서:

```bash
# 가상환경 생성
python3 -m venv .venv

# 가상환경 활성화 (macOS)
source .venv/bin/activate

# 활성화 확인 — 터미널 앞에 (.venv) 표시되면 성공
```

---

## requirements.txt 생성

VS Code에서 `requirements.txt` 파일 생성 후 아래 내용 입력:

```
msal>=1.28.0
requests>=2.31.0
python-dotenv>=1.0.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
langchain-text-splitters>=0.2.0
chromadb>=0.5.0
sentence-transformers>=3.0.0
streamlit>=1.35.0
google-genai>=1.0.0
```

라이브러리 설치:
```bash
pip install -r requirements.txt
```

---

## .env 파일 생성

프로젝트 루트에 `.env.example`의 이름을 `.env` 로 변경 후 복사해 둔 ID와 KEY 입력:

```env
# ============================
# Microsoft Graph API
# ============================
AZURE_CLIENT_ID=여기에 입력
AZURE_TENANT_ID=consumers
AZURE_CLIENT_SECRET=여기에 입력

# ============================
# GEMINI API
# ============================
GEMINI_API_KEY=여기에 입력
GEMINI_MODEL=gemini-2.5-flash

# ============================
# Embedding 설정
# ============================
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2

# ============================
# RAG DB 설정
# ============================
CHROMA_DB_PATH=./chroma_db
TOP_K_RESULTS=5
SYNC_STATE_PATH=./sync_state.json
```

---

## .gitignore 파일 생성

```
# Environment variables
.env
.claude/

# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
.Python
*.egg-info/
dist/
build/
.eggs/

# Virtual environments
venv/
.venv/
env/

# IDE
.vscode/
.idea/

# Vector store / data
*.pkl
*.faiss
chroma_db/
data/

token_cache.json
sync_state.json

```
