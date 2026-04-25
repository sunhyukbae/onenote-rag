# 2단계: Gemini API 키 발급

> Google Gemini 2.5 Flash를 RAG 답변 생성에 사용한다. 무료 티어 제공.

## 무료 한도

| 항목 | 한도 |
|------|------|
| 요청 수 | 15 requests/분 |
| 일일 한도 | 1,500 requests/일 |
| 비용 | **무료** |

---

## API 키 발급

1. https://aistudio.google.com 접속
2. Google 계정으로 로그인
3. 좌측 메뉴 → `Get API key`
4. `Create API key` 클릭
5. 생성된 키 복사

---

## .env에 입력

```env
GEMINI_API_KEY=발급받은_키
GEMINI_MODEL=gemini-2.5-flash
```
