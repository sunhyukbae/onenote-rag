# 1단계: Microsoft Graph API 설정

> OneNote 데이터에 접근하려면 Azure에 앱을 등록해야 한다.

> 💡 **참고**: 이 RAG 모델은 Mac에 로컬 저장된 OneNote 파일을
> 직접 읽지 않습니다. OneDrive에 동기화된 데이터를
> Microsoft Graph API를 통해 읽어옵니다.
> OneNote 앱에서 OneDrive 동기화가 완료된 상태인지 반드시 확인하세요.

## 1-1. Azure Free Account 생성

1. https://azure.microsoft.com/free 접속
2. Microsoft 개인 계정으로 로그인
3. 카드 정보 입력 (인증용, 즉시 청구 없음)
4. 가입 완료 → Azure AD Tenant 자동 생성

---

## 1-2. 앱 등록

1. https://portal.azure.com 접속
2. 상단 검색창 → `App registrations` 검색
3. `+ New registration` 클릭
4. 아래와 같이 입력:

| 항목 | 입력값 |
|------|--------|
| Name | `onenote-rag-app` |
| Supported account types | **"Accounts in any organizational directory... and personal Microsoft accounts"** |
| Redirect URI | `Web` / `http://localhost:8080` |

5. **Register** 클릭

---

## 1-3. 핵심 값 복사

등록 직후 화면에서:

```
Application (client) ID  →  AZURE_CLIENT_ID
Directory (tenant) ID    →  AZURE_TENANT_ID
```

> ⚠️ 이 화면을 닫기 전에 반드시 복사

---

## 1-4. API 권한 추가

1. 왼쪽 메뉴 → `API permissions`
2. `+ Add a permission` → `Microsoft Graph`
3. `Delegated permissions` 선택
4. 아래 3개 검색하여 체크:

| 권한 |
|------|
| `Notes.Read` |
| `Notes.Read.All` |
| `User.Read` |

---

## 1-5. Client Secret 생성

1. 왼쪽 메뉴 → `Certificates & secrets`
2. `+ New client secret`
3. Description: `onenote-rag-secret`, Expires: `24 months`
4. **Add** 클릭

> ⚠️ 생성 직후 **Value 열의 값을 즉시 복사** — 이 화면을 벗어나면 영구 삭제됨

---

## 1-6. Public Client Flow 허용

1. 왼쪽 메뉴 → `Authentication`
2. 스크롤 → `Advanced settings`
3. `Allow public client flows` → **Yes**
4. **Save**

---

## 1-7. .env에 입력

```env
AZURE_CLIENT_ID=복사한_CLIENT_ID
AZURE_TENANT_ID=consumers
AZURE_CLIENT_SECRET=복사한_SECRET_VALUE
```

> ⚠️ `AZURE_TENANT_ID`는 개인 OneNote 접근을 위해 반드시 `consumers`로 입력
