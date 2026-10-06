# 실행 결과의 범위

## HTTP 의미론 실습

2026-10-01, CPython 3.12.14에서 `python3 study/labs/http_semantics.py` 실행.

- GET 내용, ETag 조건부 304, 같은 연결 재사용, 다른 연결 생성, DELETE 204→404, 최종 부재 상태: 총 7개 검증 통과.
- 초기 sandbox에서는 socket 생성이 제한되어 실패했고, 허용된 실행 권한으로 재실행해 통과했습니다.
- 서버는 loopback 임시 포트이며 실행 후 종료합니다. TLS·브라우저 캐시·HTTP/2·3·인증을 시험한 것은 아닙니다.

## CPU·I/O 동시성 실습

[원본 JSON](concurrency-2026-10-01.json), [해석 자료](../03-execution/09-benchmark.md), [실행 코드](../labs/concurrency_bench.py).

실행 명령:

```bash
python3 study/labs/concurrency_bench.py --output study/results/concurrency-2026-10-01.json
```

이 파일은 이미 존재하므로 다시 실행할 때는 다른 출력 경로를 쓰세요. 덮어쓰기를 방지하도록 작성했습니다.

CPython 3.12.14, workers 4, tasks 8, repeats 3, spawn. 24개 측정 묶음의 총 192개 작업 결과가 일치했습니다. 원본 파일에 모든 표본과 환경을 기록했습니다. 풀 초기화·워밍업과 본 측정 구간을 분리했으며 실험의 메모리·꼬리 지연·운영망 성능은 측정하지 않았습니다.

## 실행하지 않은 것

브라우저 개발자 도구 관찰, 운영 DNS 변경, HTTP/2·3 비교, TLS 배포, free-threaded Python 비교, heartbeat 실험, 문서의 독자 확장 과제는 미실행입니다. 아래 실습 외의 배포·장애·운영 처리량 검증은 수행하지 않았습니다.

## FastAPI 실행 경계와 워커

모두 2026-10-01 실행. 시간 수치는 소규모 로컬 관찰값이며 운영 성능 보장이 아닙니다.

| 실습 | 원본 결과 | 확인한 범위 |
| --- | --- | --- |
| 단일 서버와 스레드풀 | [JSON](server-models-2026-10-01.json) | 실제 HTTP 8응답, 최대 동시 핸들러 1 대 4 |
| FastAPI 함수 경계 | [JSON](fastapi-boundaries-2026-10-01.json) | ASGITransport 120응답과 의존성 실행 위치; TCP 서버 성능은 아님 |
| LocalStack S3 | [JSON](localstack-s3-2026-10-01.json) | 실제 로컬 S3 HTTP 읽기 180회 결과 일치, 버킷·객체 정리 |
| Uvicorn 2워커 | [JSON](uvicorn-workers-2026-10-01.json) | 지속 연결 12회 한 PID, 새 연결 24회 두 PID, lifespan 시작·종료 각각 2회 |

LocalStack 4.0.0 컨테이너는 제거했습니다. 50ms 지연 조건은 SDK 호출 전 인위적 sleep이며 실제 S3 망 지연 측정이 아닙니다. Uvicorn 서버도 종료했습니다. 각 실습의 실행 명령·버전·해석은 4장 해당 본문에 있습니다.

## PostgreSQL 격리와 인덱스

[원본 결과](postgres-2026-10-01.json), [실행 방법](../05-database/06-isolation-lab.md). PostgreSQL 17.6, psycopg 3.2.10, 2026-10-01. 7개 격리·락 사례의 예상값과 오류 코드를 확인했습니다. Serializable 실패 후 전체 판단을 재시도해 당직자 1명 유지도 확인했습니다.

10만 행의 사용자별 최신 20개 조회는 인덱스 전 Seq Scan+Sort, 후 Index Scan을 사용했습니다. 반환 행 수는 모두 20입니다. 단일 실행의 시간은 성능 보장이 아닙니다. 실습이 만든 UUID 스키마 삭제와 연결 종료를 확인했고 컨테이너도 제거했습니다.

## OAuth/OIDC 흐름

[원본 결과](oauth-2026-10-01.json), [실습 해설](../06-auth/06-login-lab.md). 2026-10-01에 테스트 제공자와 in-process ASGITransport로 15개 시나리오를 통과했습니다. 실제 서명은 PyJWT/cryptography의 임시 RSA 키로 생성·검증했습니다. 실제 사용자 인증·브라우저 쿠키·외부 제공자 호환성·JWKS 회전은 검증하지 않았습니다.

## 캐시와 취소

[원본 결과](cache-cancellation-2026-10-01.json). 표준 라이브러리만 사용한 두 spawn 프로세스의 로컬 캐시는 A만 비우면 A=version-2, B=version-1이었습니다. 원본은 임시 파일이며 Redis는 실행하지 않았습니다. asyncio task가 timeout으로 취소된 뒤에도 스레드가 실행 중임을 확인하고 명시적으로 해제·종료했습니다.

## 두 앱 프로세스 전환

[원본 결과](blue-green-2026-10-01.json), [실습 범위](../08-deployment/08-rollout-lab.md). 진행 중 구버전 요청 3개를 보존하며 전환했습니다. 전환 40개 요청과 구버전 종료 후 10개 요청 모두 오류 0이었고, 중간에 구버전으로 되돌린 응답도 확인했습니다. 실제 두 컨테이너·nginx·ALB·Kubernetes·DB migration은 검증하지 않았습니다. 실패 후보는 모의 상태 판정입니다.

## 관측 실험

[원본 JSON](observability-2026-10-02.json), [그래프](observability-2026-10-02.png). 2026-10-02, 요청 context 분리·to_thread 전달·기본 executor 미전달을 확인했습니다. 루프 블로킹의 최대 lag 약60.284ms, 오프로딩 약0.798ms, AnyIO 토큰 peak2와6작업 완료, tracemalloc 추적 증가1,090,424바이트를 확인했습니다. 모두 짧은 합성 실험이며 Grafana/Prometheus/OTel/py-spy/memray 실행 증거는 아닙니다.

## pytest·coverage·변이 검사

2026-10-02, 교육용 가격/견적 예제의 정상 suite는 **21 passed**입니다. [coverage 원본](testing-coverage-2026-10-02.json)은 전체 문장33개 중 누락0, 분기12개 중 부분분기1, 도구 표시98%입니다.

[변이 검사](testing-mutation-2026-10-02.json)는 임시 복사본에서 무료배송 비교 `>=`를 `>`로 바꾸어 예상대로 **3 failed, 18 passed**를 확인했습니다. 이는 정상 suite 실패가 아닌 결함 탐지 검증입니다. 원본 코드는 변경하지 않았고 임시 복사본은 제거했습니다.

## 실제 HTTP 부하 실험

[원본 JSON](load-http-2026-10-02.json), [그래프](load-http-2026-10-02.png), [조건과 해석](../11-performance/04-bottleneck-lab.md). 2026-10-02, 별도 Uvicorn 1워커를 실제 loopback HTTP/1.1로 호출했습니다. closed 모델·지속 연결·think time0, 각 단계120초입니다.

| 경로 / VUser | 성공 | 오류 | 성공 RPS | p99 ms |
| --- | --- | --- | --- | --- |
| blocking / 1 | 1303 | 0 | 10.85 | 96.10 |
| blocking / 8 | 2355 | 0 | 19.56 | 522.96 |
| async wait / 8 | 10308 | 0 | 85.85 | 106.25 |

총13,966개 측정 응답의 내용·상태를 확인했습니다. warmup은 별도이며 RPS분모에는 drain을 포함합니다. 합성50ms 대기, 같은 머신의 발생기, 고정 순서 단일 시행입니다. 고정 도착률·실제 외부 I/O·장기 soak·운영 용량은 검증하지 않았습니다. 서버·소켓은 정리했습니다.

## 리팩토링 검증

[원본 결과](refactor-2026-10-02.json), [실습](../13-coding/04-refactoring.md). 2026-10-02, 임시 복사본의 가격 모듈에서 계산 세 단계를 함수로 추출하고 기존21개 테스트를 그대로 실행하여 모두 통과했습니다. 원본 코드 바이트가 유지되고 임시 복사본이 제거되었음을 확인했습니다. 전체 입력 동치나 성능 개선을 증명한 것은 아닙니다.

## Python / FastAPI 트랙 보강 (2026-10-06)

[JUnit 원본](python-track-2026-10-06.xml), [9-7 계측 연결](../09-observability/07-live-metrics.md), [10-7 테스트 도구](../10-testing/07-python-toolkit.md).

`/workspace/study-track/bin/python -m pytest -q -c study/labs/python_track_tests/pytest.ini study/labs/python_track_tests --junitxml=study/results/python-track-2026-10-06.xml` 실행: **7 passed**, botocore 1.35.99의 `datetime.utcnow` deprecation 경고 11건.

- moto S3의 빈/텍스트/바이너리 왕복 3개와 NoSuchKey/404 1개.
- polyfactory 객체 독립성 1개, 주입한 시계의 TTL 경계 1개.
- ASGI exporter 1개: 루프 지연 표본, AnyIO 토큰 2개, 응답 6개 완료, delay 범위 422, Prometheus 본문과 RSS 이름 확인.

Prometheus 설정 YAML과 Grafana JSON은 제공했지만 수집기·Grafana 서버를 실행한 결과는 아닙니다. 실제 AWS·aioboto3·OTel Collector·py-spy·memray 검증도 포함하지 않았습니다. 직접 의존성은 `labs/requirements-python-track.txt`에 기록했으며, 기존 패키지를 변경하지 않는 별도 가상환경에 설치했습니다.
