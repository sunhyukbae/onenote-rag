onenote-rag/
├── README.md                    ← 메인 허브
├── docs/
│   ├── 01_prerequisites.md      ← 사전 준비
│   ├── 02_azure_setup.md        ← Microsoft Graph API 설정
│   ├── 03_gemini_setup.md       ← Gemini API 키 발급
│   ├── 04_vscode_setup.md       ← VS Code + Claude Code 설정
│   ├── 05_project_setup.md      ← 프로젝트 생성 + venv
│   ├── 06_coding.md             ← Claude Code로 코딩
│   ├── 07_run_and_test.md       ← 실행 및 테스트
│   └── 08_architecture.md       ← 아키텍처 설명
├── .env.example                 ← .env 템플릿 (실제 .env는 .gitignore)
├── .gitignore
├── requirements.txt
├── app.py
├── graph_client.py
├── ingestor.py
├── rag_engine.py
├── vector_store.py
└── embedder.py