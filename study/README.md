# 데이터팀 개발 공부 자료

사용자가 제공한 13개 대단원의 순서를 따라, 한 소단원씩 읽고 적용하고 확인하는 학습 자료입니다. 원문 웹페이지 대신 대화에 제공된 목차와 OAuth 그림을 범위의 기준으로 삼았습니다.

- [전체 소단원·작성 계획](PLAN.md)
- [공통편 이후 Python / FastAPI 트랙 — 항목별 대응과 보강 내역](PYTHON_FASTAPI_TRACK.md)

## 1. 코딩 스타일과 팀 생활

| 소단원 | 학습 자료 | 퀴즈 해설 |
| --- | --- | --- |
| 1-1 | [코딩 스타일이 다를 때 합의하기](01-team/01-style.md) | [정답·해설](01-team/01-style-answers.md) |
| 1-2 | [설계 의견이 다를 때 결정하기](01-team/02-design.md) | [정답·해설](01-team/02-design-answers.md) |
| 1-3 | [모르는 것을 언제 어떻게 질문할까](01-team/03-questions.md) | [정답·해설](01-team/03-questions-answers.md) |
| 1-4 | [계몽과 전염: 팀의 변화를 만드는 방법](01-team/04-change.md) | [정답·해설](01-team/04-change-answers.md) |
| 1-5 | [성장: 배우기와 버리기](01-team/05-growth.md) | [정답·해설](01-team/05-growth-answers.md) |
| 1-6 | [기능 구현과 기술부채의 우선순위](01-team/06-debt.md) | [정답·해설](01-team/06-debt-answers.md) |
| 1-7 | [변화하는 스펙을 어떻게 문서화할까](01-team/07-docs.md) | [정답·해설](01-team/07-docs-answers.md) |
| 1-8 | [배운 것을 업무에 적용하기](01-team/08-apply.md) | [정답·해설](01-team/08-apply-answers.md) |

## 2. 네트워크

| 소단원 | 학습 자료 | 퀴즈 해설 |
| --- | --- | --- |
| 2-1 | [주소창 입력에서 화면 표시까지](02-network/01-navigation.md) | [정답·해설](02-network/01-navigation-answers.md) |
| 2-2 | [패킷·라우터·해저광케이블](02-network/02-packets.md) | [정답·해설](02-network/02-packets-answers.md) |
| 2-3 | [DNS 등록과 이름 해석](02-network/03-dns.md) | [정답·해설](02-network/03-dns-answers.md) |
| 2-4 | [TCP/IP와 UDP](02-network/04-transport.md) | [정답·해설](02-network/04-transport-answers.md) |
| 2-5 | [연결 재사용과 커넥션 풀](02-network/05-connections.md) | [정답·해설](02-network/05-connections-answers.md) |
| 2-6 | [HTTP와 stateless](02-network/06-http.md) | [정답·해설](02-network/06-http-answers.md) |
| 2-7 | [HTTPS와 TLS](02-network/07-tls.md) | [정답·해설](02-network/07-tls-answers.md) |
| 2-8 | [HTTP/1.1과 주요 헤더](02-network/08-headers.md) | [정답·해설](02-network/08-headers-answers.md) |
| 2-9 | [HTTP/1.1·HTTP/2·HTTP/3 비교](02-network/09-http-versions.md) | [정답·해설](02-network/09-http-versions-answers.md) |

## 3. 기초: 내 코드는 어떻게 실행되나

| 소단원 | 학습 자료 | 퀴즈 해설 |
| --- | --- | --- |
| 3-1 | [CPU·메모리·OS의 역할](03-execution/01-hardware-os.md) | [정답·해설](03-execution/01-hardware-os-answers.md) |
| 3-2 | [프로세스·스레드·컨텍스트 스위칭](03-execution/02-process-thread.md) | [정답·해설](03-execution/02-process-thread-answers.md) |
| 3-3 | [동시성과 병렬성](03-execution/03-concurrency.md) | [정답·해설](03-execution/03-concurrency-answers.md) |
| 3-4 | [CPU 바운드와 I/O 바운드](03-execution/04-waiting.md) | [정답·해설](03-execution/04-waiting-answers.md) |
| 3-5 | [블로킹·논블로킹, 동기·비동기](03-execution/05-sync-async.md) | [정답·해설](03-execution/05-sync-async-answers.md) |
| 3-6 | [기다림을 활용하는 세 가지 방법](03-execution/06-strategies.md) | [정답·해설](03-execution/06-strategies-answers.md) |
| 3-7 | [코루틴과 이벤트루프 막힘](03-execution/07-coroutines.md) | [정답·해설](03-execution/07-coroutines-answers.md) |
| 3-8 | [GIL의 범위와 예외](03-execution/08-gil.md) | [정답·해설](03-execution/08-gil-answers.md) |
| 3-9 | [CPU·I/O 동시성 비교 실습](03-execution/09-benchmark.md) | [정답·해설](03-execution/09-benchmark-answers.md) |

## 4. FastAPI와 동기/비동기

| 소단원 | 학습 자료 | 퀴즈 해설 |
| --- | --- | --- |
| 4-1 | [작은 HTTP 서버와 스레드풀](04-fastapi/01-basic-server.md) | [정답·해설](04-fastapi/01-basic-server-answers.md) |
| 4-2 | [def와 async def의 실행 위치](04-fastapi/02-def-async.md) | [정답·해설](04-fastapi/02-def-async-answers.md) |
| 4-3 | [비동기 함수 안의 동기 SDK](04-fastapi/03-blocking-sdk.md) | [정답·해설](04-fastapi/03-blocking-sdk-answers.md) |
| 4-4 | [LocalStack S3 동시 요청 실습](04-fastapi/04-localstack.md) | [정답·해설](04-fastapi/04-localstack-answers.md) |
| 4-5 | [Uvicorn 워커와 연결 분산](04-fastapi/05-workers.md) | [정답·해설](04-fastapi/05-workers-answers.md) |
| 4-6 | [스레드풀·HTTP 풀·비동기 SDK](04-fastapi/06-pools.md) | [정답·해설](04-fastapi/06-pools-answers.md) |
| 4-7 | [자원 생명주기와 프로세스 시작](04-fastapi/07-lifecycle.md) | [정답·해설](04-fastapi/07-lifecycle-answers.md) |

## 5. DB

| 소단원 | 학습 자료 | 퀴즈 해설 |
| --- | --- | --- |
| 5-1 | [저장소 종류와 선택 기준](05-database/01-stores.md) | [정답·해설](05-database/01-stores-answers.md) |
| 5-2 | [정규화와 데이터 무결성](05-database/02-normalization.md) | [정답·해설](05-database/02-normalization-answers.md) |
| 5-3 | [역정규화와 읽기 모델](05-database/03-read-models.md) | [정답·해설](05-database/03-read-models-answers.md) |
| 5-4 | [트랜잭션과 ACID](05-database/04-transactions.md) | [정답·해설](05-database/04-transactions-answers.md) |
| 5-5 | [격리 수준과 동시성 이상](05-database/05-isolation.md) | [정답·해설](05-database/05-isolation-answers.md) |
| 5-6 | [PostgreSQL 두 세션 실습](05-database/06-isolation-lab.md) | [정답·해설](05-database/06-isolation-lab-answers.md) |
| 5-7 | [인덱스와 실행계획](05-database/07-indexes.md) | [정답·해설](05-database/07-indexes-answers.md) |
| 5-8 | [DB 커넥션 풀 예산](05-database/08-pool-budget.md) | [정답·해설](05-database/08-pool-budget-answers.md) |

## 6. 인증

| 소단원 | 학습 자료 | 퀴즈 해설 |
| --- | --- | --- |
| 6-1 | [인증·인가·OAuth·OIDC](06-auth/01-authentication.md) | [정답·해설](06-auth/01-authentication-answers.md) |
| 6-2 | [Authorization Code + PKCE](06-auth/02-code-pkce.md) | [정답·해설](06-auth/02-code-pkce-answers.md) |
| 6-3 | [콜백과 토큰 검증](06-auth/03-validation.md) | [정답·해설](06-auth/03-validation-answers.md) |
| 6-4 | [서버 세션과 JWT](06-auth/04-sessions.md) | [정답·해설](06-auth/04-sessions-answers.md) |
| 6-5 | [토큰 수명과 계정 연결](06-auth/05-token-lifecycle.md) | [정답·해설](06-auth/05-token-lifecycle-answers.md) |
| 6-6 | [로그인 흐름 검증 실습](06-auth/06-login-lab.md) | [정답·해설](06-auth/06-login-lab-answers.md) |

## 7. 캐시와 타임아웃

| 소단원 | 학습 자료 | 퀴즈 해설 |
| --- | --- | --- |
| 7-1 | [로컬 캐시와 공유 캐시](07-cache-timeouts/01-local-shared.md) | [정답·해설](07-cache-timeouts/01-local-shared-answers.md) |
| 7-2 | [캐시 갱신과 장애](07-cache-timeouts/02-invalidation.md) | [정답·해설](07-cache-timeouts/02-invalidation-answers.md) |
| 7-3 | [구간별 타임아웃 예산](07-cache-timeouts/03-timeout-budget.md) | [정답·해설](07-cache-timeouts/03-timeout-budget-answers.md) |
| 7-4 | [취소 전파와 스레드](07-cache-timeouts/04-cancellation.md) | [정답·해설](07-cache-timeouts/04-cancellation-answers.md) |
| 7-5 | [재시도와 과부하](07-cache-timeouts/05-retries.md) | [정답·해설](07-cache-timeouts/05-retries-answers.md) |

## 8. Web / Proxy / 배포

| 소단원 | 학습 자료 | 퀴즈 해설 |
| --- | --- | --- |
| 8-1 | [리버스 프록시와 앱 서버](08-deployment/01-proxy.md) | [정답·해설](08-deployment/01-proxy-answers.md) |
| 8-2 | [Docker 이미지 만들기](08-deployment/02-docker.md) | [정답·해설](08-deployment/02-docker-answers.md) |
| 8-3 | [컨테이너 자원과 워커 수](08-deployment/03-resources.md) | [정답·해설](08-deployment/03-resources-answers.md) |
| 8-4 | [Jenkins 기반 원격 배포](08-deployment/04-jenkins.md) | [정답·해설](08-deployment/04-jenkins-answers.md) |
| 8-5 | [Ansible과 반복 가능한 변경](08-deployment/05-ansible.md) | [정답·해설](08-deployment/05-ansible-answers.md) |
| 8-6 | [이미지 배포·Kubernetes·GitOps](08-deployment/06-gitops.md) | [정답·해설](08-deployment/06-gitops-answers.md) |
| 8-7 | [배포 전략과 종료 절차](08-deployment/07-strategies.md) | [정답·해설](08-deployment/07-strategies-answers.md) |
| 8-8 | [두 앱 인스턴스 전환 실습](08-deployment/08-rollout-lab.md) | [정답·해설](08-deployment/08-rollout-lab-answers.md) |

## 9. 로깅 / 모니터링

| 소단원 | 학습 자료 | 퀴즈 해설 |
| --- | --- | --- |
| 9-1 | [구조화 로그와 request-id](09-observability/01-logging.md) | [정답·해설](09-observability/01-logging-answers.md) |
| 9-2 | [contextvars와 실행 경계](09-observability/02-contextvars.md) | [정답·해설](09-observability/02-contextvars-answers.md) |
| 9-3 | [로그·메트릭·트레이스](09-observability/03-signals.md) | [정답·해설](09-observability/03-signals-answers.md) |
| 9-4 | [병목을 보여 주는 지표](09-observability/04-bottleneck-metrics.md) | [정답·해설](09-observability/04-bottleneck-metrics-answers.md) |
| 9-5 | [고장을 주입하고 관찰하기](09-observability/05-fault-lab.md) | [정답·해설](09-observability/05-fault-lab-answers.md) |
| 9-6 | [프로파일링 도구 선택](09-observability/06-profiling.md) | [정답·해설](09-observability/06-profiling-answers.md) |
| 9-7 | [Python 지표를 Prometheus·Grafana로 연결하기](09-observability/07-live-metrics.md) | [정답·해설](09-observability/07-live-metrics-answers.md) |

## 10. 테스트

| 소단원 | 학습 자료 | 퀴즈 해설 |
| --- | --- | --- |
| 10-1 | [pytest의 기본 단위](10-testing/01-pytest.md) | [정답·해설](10-testing/01-pytest-answers.md) |
| 10-2 | [비동기 테스트와 수명](10-testing/02-async-lifecycle.md) | [정답·해설](10-testing/02-async-lifecycle-answers.md) |
| 10-3 | [테스트 데이터와 factory](10-testing/03-factories.md) | [정답·해설](10-testing/03-factories-answers.md) |
| 10-4 | [AWS 대역과 호환 환경](10-testing/04-aws-doubles.md) | [정답·해설](10-testing/04-aws-doubles-answers.md) |
| 10-5 | [단위·통합·계약·E2E](10-testing/05-test-layers.md) | [정답·해설](10-testing/05-test-layers-answers.md) |
| 10-6 | [커버리지와 회귀 방지](10-testing/06-coverage.md) | [정답·해설](10-testing/06-coverage-answers.md) |
| 10-7 | [moto·AnyIO·polyfactory 통합 테스트](10-testing/07-python-toolkit.md) | [정답·해설](10-testing/07-python-toolkit-answers.md) |

## 11. 성능 테스트

| 소단원 | 학습 자료 | 퀴즈 해설 |
| --- | --- | --- |
| 11-1 | [도구와 부하 모델](11-performance/01-load-models.md) | [정답·해설](11-performance/01-load-models-answers.md) |
| 11-2 | [재현 가능한 시나리오](11-performance/02-scenarios.md) | [정답·해설](11-performance/02-scenarios-answers.md) |
| 11-3 | [지표 해석과 용량 판단](11-performance/03-metrics.md) | [정답·해설](11-performance/03-metrics-answers.md) |
| 11-4 | [FastAPI 병목 맞히기](11-performance/04-bottleneck-lab.md) | [정답·해설](11-performance/04-bottleneck-lab-answers.md) |
| 11-5 | [개선 검증과 회귀 기준](11-performance/05-improvement.md) | [정답·해설](11-performance/05-improvement-answers.md) |

## 12. 아키텍처 설계해보기

| 소단원 | 학습 자료 | 퀴즈 해설 |
| --- | --- | --- |
| 12-1 | [네이버 메인 요구사항 정하기](12-architecture/01-requirements.md) | [정답·해설](12-architecture/01-requirements-answers.md) |
| 12-2 | [트래픽·데이터·서버 수 추정](12-architecture/02-capacity.md) | [정답·해설](12-architecture/02-capacity-answers.md) |
| 12-3 | [저장·조회·비동기 처리 구조](12-architecture/03-data-flow.md) | [정답·해설](12-architecture/03-data-flow-answers.md) |
| 12-4 | [우리 스택의 처리 한도](12-architecture/04-stack-limits.md) | [정답·해설](12-architecture/04-stack-limits-answers.md) |
| 12-5 | [실패·일관성·운영 설계](12-architecture/05-failures.md) | [정답·해설](12-architecture/05-failures-answers.md) |
| 12-6 | [설계 리뷰와 수정](12-architecture/06-design-review.md) | [정답·해설](12-architecture/06-design-review-answers.md) |

## 13. 코딩 스킬과 습관

| 소단원 | 학습 자료 | 퀴즈 해설 |
| --- | --- | --- |
| 13-1 | [읽기 좋은 코드·불변성·순수 함수](13-coding/01-readable-pure.md) | [정답·해설](13-coding/01-readable-pure-answers.md) |
| 13-2 | [파이썬스러움과 과한 마법](13-coding/02-pythonic.md) | [정답·해설](13-coding/02-pythonic-answers.md) |
| 13-3 | [문제에서 출발하는 디자인 패턴](13-coding/03-patterns.md) | [정답·해설](13-coding/03-patterns-answers.md) |
| 13-4 | [테스트로 감싸고 리팩토링하기](13-coding/04-refactoring.md) | [정답·해설](13-coding/04-refactoring-answers.md) |
| 13-5 | [매일 15분 코드 읽기](13-coding/05-reading.md) | [정답·해설](13-coding/05-reading-answers.md) |

현재 작성 완료: **1~13장 전체 90편**. 모든 소단원에 퀴즈 5문항과 별도 해설이 있습니다(**총 450문항**). [아키텍처 설계 워크북](templates/architecture-workbook.md)으로 최종 설계를 정리할 수 있습니다.

[실행 결과와 한계](results/README.md): HTTP·동시성·FastAPI·DB·인증·캐시·배포 전환·관측·pytest 실습의 실제 결과와 미실행 범위를 기록했습니다. 독자 관찰 과제와 실행한 실험을 구분했습니다.

## 공부 방법

Python 기초 문법과 함수 사용 경험이 있는 독자를 기본 대상으로 합니다. 네트워크·운영체제·DB 경험은 필수로 가정하지 않습니다. 낯선 용어는 해당 소단원에서 풀어 설명합니다.

1. 학습 목표와 도입 사례를 보고 자신의 답을 먼저 적습니다.
2. 설명과 대안 비교를 읽고, 선택이 달라지는 조건을 표시합니다.
3. 토론 또는 실습을 수행하고 결과를 짧게 기록합니다.
4. 해설을 닫은 채 퀴즈를 풉니다.
5. 틀린 개념을 복습하고, 조건을 바꾼 사례에도 같은 판단을 적용할 수 있는지 확인합니다.

읽기·토론형은 한 편에 약 30~50분, 실습형은 약 60~90분을 예상합니다. 개인별 차이가 큰 학습용 추정치이며 일정 약속은 아닙니다. 모든 편을 한 번에 읽기보다 한 편씩 결과물을 남기는 것을 권합니다.

## 자료의 구분

- **확인한 출처의 주장:** 실제 문서의 주장을 출처와 함께 요약합니다.
- **학습용 논증:** 출처를 바탕으로 구성한 반박·재반박입니다. 저자의 실제 발언이나 실제 토론 기록으로 표시하지 않습니다.
- **설명·권장안:** 상황을 종합한 이 자료의 제안입니다. 보편적인 정답과 구분합니다.
- **실습 결과:** 직접 실행한 결과만 실행 환경과 함께 기록합니다. 예상 결과는 예상이라고 표시합니다.

실습은 필요한 편에 추가합니다. 현재 HTTP 실습은 표준 라이브러리만 사용하며 임시 로컬 서버는 실행 후 종료합니다. FastAPI 실습 의존성은 `labs/requirements-fastapi.txt`, S3 실습 의존성은 `labs/requirements-s3.txt`에 기록했습니다. boto3는 별도 가상환경에 설치했고 LocalStack 이미지를 받아 검증했습니다. 실습 서비스는 검증 후 종료했습니다.
