# 0단계: 사전 준비

## 필요한 계정

| 서비스 | 용도 | 비용 |
|--------|------|------|
| Microsoft 개인 계정 | OneNote 접근 | 무료 |
| Azure Free Account | Graph API 앱 등록 | 무료 |
| Google 계정 | Gemini API | 무료 |
| GitHub 계정 | 코드 저장 | 무료 |

---

## 설치할 소프트웨어

### 1. Python 3.11 이상
```bash
# 설치 확인
python3 --version

# 미설치 시: https://www.python.org/downloads/
```

### 2. VS Code
https://code.visualstudio.com 에서 다운로드

### 3. Git
```bash
# 설치 확인
git --version

# 미설치 시
brew install git
```

---

## VS Code Extension 설치

VS Code 실행 후 왼쪽 Extensions 아이콘(⬛⬛) 클릭:

| Extension | 검색어 |
|-----------|--------|
| Claude Code for VS Code | `Claude Code for VS Code` |
| Python | `Python` (Microsoft) |
| Pylance | `Pylance` |
| Python Debugger | `Python Debugger` |

---

## requirements.txt

프로젝트에서 사용하는 Python 라이브러리 전체 목록:

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

터미널에서 설치:
```bash
pip install -r requirements.txt
```
