# 6-2. Authorization Code + PKCE 흐름 — 정답·해설

[본문](02-code-pkce.md) · [목차](../README.md)

## Q1 — 1점

S256 방식에서는 verifier의 SHA256 바이트를 base64url로 바꾼 challenge를 보냅니다. verifier는 token 교환 때 보냅니다.

## Q2 — 1점

아닙니다. 사용자가 번들을 볼 수 있어 그 값은 숨겨진 자격증명이 아닙니다.

## Q3 — 2점

client_id, 정확한 redirect_uri, response_type=code, scope=openid, state, nonce, challenge/method 중 네 가지. 값과 역할을 두 쌍씩 맞히면 각 1점입니다.

## Q4 — 2점

client 인증은 client의 자격 확인(1점), PKCE는 인가 시도와 code 교환의 verifier 연결(1점)입니다. 둘을 대체관계로 설명하면 감점합니다.

## Q5 — 4점

각 1점: 로그인 시도 생성·브라우저 연결, state/만료/code 교환과 PKCE, OIDC 서명·claim 검증, issuer+sub 계정 매핑 후 안전한 자체 세션. 자체 JWT만 가능하다고 하면 마지막 점수를 주지 않습니다.

8점 미만이면 틀린 질문과 관련된 본문을 복습하고, 조건을 하나 바꿨을 때 답이 달라지는 이유를 적으세요. 서술형은 제품 이름보다 제약·근거·비용·검증 방법을 평가합니다.
