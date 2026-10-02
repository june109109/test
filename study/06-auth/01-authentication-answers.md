# 6-1. 인증·인가·OAuth·OIDC — 정답·해설

[본문](01-authentication.md) · [목차](../README.md)

## Q1 — 1점

OAuth는 권한 위임, OIDC는 그 위에서 인증 결과를 전달하는 계층입니다.

## Q2 — 1점

아닙니다. ID token의 대상은 인증을 요청한 client이며 API가 요구하는 access token의 용도·audience와 다릅니다.

## Q3 — 2점

access token은 의도된 resource server/API 접근용(1점), refresh token은 authorization server의 토큰 갱신용(1점)입니다.

## Q4 — 2점

각 1점: 계정 정지, 서비스 역할, 테넌트 소속, 요청 객체의 소유권 등 두 가지. 로그인 성공은 모든 데이터 접근 허용이 아닙니다.

## Q5 — 4점

각 1점: OIDC 인증 결과 검증, 서비스 세션과 캘린더 access token 분리, 최소 scope/별도 동의, 철회·갱신·실패 정책. 캘린더 토큰을 우리 서비스 관리자 권한 증거로 쓰지 않습니다.

8점 미만이면 틀린 질문과 관련된 본문을 복습하고, 조건을 하나 바꿨을 때 답이 달라지는 이유를 적으세요. 서술형은 제품 이름보다 제약·근거·비용·검증 방법을 평가합니다.
