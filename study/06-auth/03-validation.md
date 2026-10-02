# 6-3. 콜백과 토큰 검증

[목차](../README.md) · [정답·해설](03-validation-answers.md)

예상 60분. 목표: 각 검증이 막는 문제를 설명하고, JWT decode와 신뢰 검증을 구분합니다.

## 1. 브라우저가 보냈다고 신뢰하지 않는다

callback query는 외부 입력입니다. 성공 code뿐 아니라 error, state 누락, 여러 탭의 서로 다른 로그인 시도, 만료·재사용 요청을 처리해야 합니다. 예측 불가능한 로그인 시도 값을 서버 측 또는 안전하게 보호된 상태에 저장하고, 그 시도를 시작한 브라우저 세션에 연결합니다.

state가 저장소 어딘가에 존재한다는 것만으로 충분하지 않습니다. 다른 브라우저가 시작한 시도를 현재 사용자에게 붙이면 로그인 CSRF·계정 혼동 문제가 생깁니다. 비교 후 한 번만 소비하고 동시 callback에서도 원자적으로 처리합니다.

## 2. 비슷해 보이는 값의 다른 역할

| 장치 | 주된 연결 | 한계 |
| --- | --- | --- |
| state | 인가 요청과 callback, 앱의 로그인 시도 | 토큰 서명 검증을 대신하지 않음 |
| PKCE | code 발급과 verifier 보유 client | 토큰의 aud·만료 검사와 다름 |
| OIDC nonce | 로그인 시도와 ID token | 자체 API 인가를 대신하지 않음 |
| redirect URI 검증 | code가 도착할 허용 목적지 | callback 내부 검증을 없애지 않음 |
| issuer·audience | 누가 누구에게 발급했는가 | 서명만 유효해도 별도로 필요 |

RFC 9700은 조건을 충족하는 PKCE나 OIDC nonce로 CSRF 보호를 제공하는 방식을 다룹니다. 따라서 ‘모든 구현에서 state만이 유일한 방어’라는 설명은 정확하지 않습니다. 이 교재는 이해와 추적이 쉬운 명시적 state+브라우저 바인딩에 PKCE·nonce를 함께 사용합니다.

## 3. ID token 검증 순서와 설정

검증된 OIDC 라이브러리를 쓰되 어떤 정책을 적용하는지 알아야 합니다.

1. 신뢰하는 제공자 설정에서 issuer·token endpoint·키 출처를 고정합니다.
2. 허용한 알고리즘과 신뢰한 키로 서명을 검증합니다. 토큰이 제안한 임의 URL에서 키를 가져오지 않습니다.
3. `iss`가 기대한 issuer와 정확히 일치하고 `aud`가 우리 client를 포함하는지 확인합니다. 여러 audience 및 `azp` 규칙도 OIDC에 맞게 처리합니다.
4. `exp`, 필요한 `iat`/인증 시각 정책, nonce 일치를 검사합니다. 허용 clock skew는 작은 명시적 범위로 둡니다.
5. `sub`의 존재·형식과 제공자 계정 매핑을 검사합니다. UserInfo를 쓰면 그 sub도 ID token과 일치해야 합니다.

base64 decode로 payload를 읽는 것은 검증이 아닙니다. 서명만 맞아도 다른 client에게 발급된 토큰이거나 이미 만료된 토큰일 수 있습니다. ID token과 access token을 같은 검증 함수에 무분별하게 넣지 않습니다.

## 4. 키 회전과 오류 처리

JWKS는 신뢰한 제공자가 공개키를 게시하는 방식입니다. `kid`로 키를 고르되 모르는 kid가 올 때 무제한 원격 조회를 해서는 안 됩니다. 제한된 갱신·캐시·오류 처리가 필요합니다. 키 회전 기간에 이전 키와 새 키가 공존할 수 있습니다.

검증 실패 시 로그인 세션을 발급하지 않고 안전한 재시작 경로를 제공합니다. 운영 로그에는 오류 분류·request-id 정도를 남기고 code·verifier·전체 token·민감 claim은 빼세요. callback URL 전체를 access log에 남기는 기본 설정도 확인합니다.

## 5. 적용 과제

다른 client의 정상 서명 ID token, 잘못된 state, 정상 state이지만 다른 nonce, 신뢰하지 않는 키 URL이 포함된 토큰을 각각 어디서 거부할지 표시하세요. ‘서명 검증’ 한 단어로 모든 항목을 덮지 않습니다.

## 퀴즈

### Q1

JWT payload를 decode하는 것과 신뢰 검증은 같은가?

### Q2

서명이 맞는데 aud가 다른 client라면 허용하는가?

### Q3

state와 nonce가 각각 연결하는 것은?

### Q4

알 수 없는 kid마다 무제한 JWKS 조회를 하면 어떤 문제가 있는가?

### Q5

callback부터 로그인 세션 생성까지 검증 순서와 실패 처리를 설계하라.

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- [OAuth Security BCP, RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html) — 현대 OAuth 보안 권고.
- [PKCE, RFC 7636](https://www.rfc-editor.org/rfc/rfc7636.html).
- [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html) — 인증 계층·ID token·검증 규칙.

확인일: 2026-10-01. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
