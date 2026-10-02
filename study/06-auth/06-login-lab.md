# 6-6. 로그인 흐름 검증 실습

[목차](../README.md) · [정답·해설](06-login-lab-answers.md)

예상 70분. 목표: 성공 경로뿐 아니라 거부·재전송·잘못된 토큰을 검사하고, 테스트 제공자의 검증 범위를 설명합니다.

## 1. 무엇을 실제로 실행했나

[실행 코드](../labs/oauth_flow.py), [원본 결과](../results/oauth-2026-10-01.json), [의존성](../labs/requirements-auth.txt).

FastAPI로 인가·token endpoint를 가진 **테스트용 제공자**를 만들고 httpx ASGITransport로 호출했습니다. 실제 외부 네트워크나 브라우저는 사용하지 않았습니다. `.invalid` 도메인은 앱 내부 요청 구분용이며 접속 가능한 웹사이트가 아닙니다.

제공자는 가상의 고정 계정 하나를 사용합니다. 사용자의 실제 비밀번호·신원을 확인하지 않습니다. 이 코드를 운영 인증 서버나 완전한 OIDC 구현으로 사용하지 않습니다.

```bash
python3 -m venv /tmp/study-auth-venv
/tmp/study-auth-venv/bin/python -m pip install -r study/labs/requirements-auth.txt
/tmp/study-auth-venv/bin/python study/labs/oauth_flow.py   --output /tmp/oauth-new.json
```

실제 검증은 기존 Python 환경의 PyJWT 2.13.0, cryptography 50.0.0, httpx 0.28.1, FastAPI 0.141.1로 수행했습니다. 위 명령은 같은 직접 의존성을 새 가상환경에 설치하는 재현 경로입니다. JSON 출력 경로가 있으면 덮어쓰지 않습니다.

## 2. 구현 경계

테스트 제공자는 실행할 때 임시 RSA 키를 만들고 ID token을 RS256으로 서명합니다. client는 이 제공자의 공개키를 신뢰하도록 직접 전달받습니다. 토큰이 알려 주는 임의 키 주소를 사용하지 않습니다. 키는 메모리에서만 쓰며 출력하지 않습니다.

state·verifier·nonce는 로그인 시도마다 새로 만들고 시도 만료와 가상의 browser ID에 연결합니다. browser ID는 실제 cookie 검증을 대신하는 **시험 장치**입니다. code와 로그인 시도는 일회 사용합니다. PKCE는 S256을 확인합니다.

client는 secret을 쓰지 않는 public client 모델입니다. 6-2의 confidential backend 그림과 달리 client 인증을 생략했으며 이를 모든 백엔드의 교환 방법으로 일반화하지 않습니다. ID token의 단일 audience·고정 issuer·서명·만료·nonce·sub를 검사합니다. 전체 OIDC 규격의 다중 aud/azp·discovery·JWKS 회전은 구현하지 않았습니다.

## 3. 실제 15개 검증 결과

| 분류 | 검증한 항목 |
| --- | --- |
| 성공 1개 | code + 올바른 PKCE + ID token 검증 후 issuer/sub 반환 |
| callback 5개 | 재사용, 동의 거부, 모르는 state, 다른 browser, 만료 시도 거부 |
| code 교환 3개 | 잘못된 verifier, code 재사용, redirect URI 불일치 거부 |
| authorize 1개 | 미등록 redirect를 거부하고 그 주소로 redirect하지 않음 |
| token 5개 | 잘못된 issuer·audience·만료·nonce·서명 거부 |

2026-10-01, 15개 모두 통과했습니다. ‘잘못된 서명’ 검증은 다른 RSA 개인키로 서명한 token으로 수행했습니다. JSON 파일에는 토큰·코드·키 값을 남기지 않고 검사 이름과 버전만 저장합니다.

## 4. 성공해도 아직 모르는 것

실제 제공자는 scope·등록 client·인증 방법·동의·오류 정책이 다릅니다. 브라우저에서는 SameSite·cookie domain·HTTPS·CORS·프록시 헤더가 영향을 줍니다. 키 회전·refresh·동시 callback·여러 워커의 상태 저장도 별도 검증이 필요합니다.

이 실습의 `dict`는 단일 프로세스 시험용입니다. 운영에서 여러 워커가 state를 공유하고 원자적으로 소비해야 하는 문제를 해결하지 않습니다. 실제 로그인 세션 쿠키도 발급하지 않고 검증된 `(issuer, subject)`를 반환하는 데서 끝납니다.

## 5. 적용 과제

실제 제공자 sandbox로 옮긴다고 가정하고 계약 테스트 목록을 만드세요. 등록 callback, 실제 HTTPS, 사용자 동의 거부, 멀티탭, 여러 워커, 키 회전, 제공자 장애를 추가하세요. 먼저 테스트 제공자에 있는 가정 중 어느 것이 달라지는지 기록합니다.

## 퀴즈

### Q1

15개 검증 통과는 실제 구글·카카오 로그인 호환성의 증거인가?

### Q2

이 실습은 실제 브라우저 쿠키의 SameSite 동작을 검사하는가?

### Q3

고정 공개키 검증과 JWKS 회전 검증의 차이는?

### Q4

다른 browser ID의 state를 거부하는 검증은 무엇을 모델링하는가?

### Q5

이 실습을 실제 서비스 통합 검증으로 확장할 때 필요한 네 가지 검사를 제안하라.

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- [OAuth Security BCP, RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html) — 현대 OAuth 보안 권고.
- [PKCE, RFC 7636](https://www.rfc-editor.org/rfc/rfc7636.html).
- [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html) — 인증 계층·ID token·검증 규칙.
- 이 편의 실행 증거는 원본 JSON과 코드입니다. 실제 인증 제품의 보안 인증이나 운영 적합성 판정이 아닙니다.

확인일: 2026-10-01. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
