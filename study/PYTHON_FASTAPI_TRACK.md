# 공통편 다음에 읽는 Python / FastAPI 트랙

[전체 목차](README.md) · [작성 계획](PLAN.md)

2026-10-06에 사용자가 제공한 목록을 기존 88편과 대조했습니다. **핵심 개념은 모두 포함되어 있었습니다.** 다만 라이브러리 이름·선택 기준만 설명한 부분과 실행 예제까지 있는 부분이 달랐습니다. 기존 18개 소단원을 보강하고, 수집기/대시보드 연결과 Python 테스트 도구 통합을 각각 **9-7·10-7**로 추가했습니다. 현재 총 90편입니다.

공통 네트워크·OS·DB·인증을 이미 공부했다면 아래 순서로 이동하세요. 번호는 기존 공통편과의 연결을 위해 유지합니다.

## 1. 파이썬 런타임과 동시성

| 요청한 항목 | 읽을 단원 | 포함 여부와 보강 |
| --- | --- | --- |
| 코루틴 | [3-7 코루틴과 이벤트루프](03-execution/07-coroutines.md) | 기존 포함. coroutine/Task/TaskGroup·취소 수명 연결 보강 |
| 동기/비동기 × 블로킹/논블로킹 2×2 | [3-5 용어와 2×2](03-execution/05-sync-async.md) | 기존 포함. API·호출 스레드·완료의 정의를 먼저 읽기 |
| 이벤트루프 막힘 | [3-7](03-execution/07-coroutines.md), [9-5 관측](09-observability/05-fault-lab.md) | 기존 실험과 그래프 있음. [9-7](09-observability/07-live-metrics.md)에 exporter 추가 |
| GIL·I/O 대기·CPU는 프로세스로 | [3-8 GIL](03-execution/08-gil.md) | 기존 포함. 확장 모듈·free-threaded·직렬화 비용에 따른 선택 보강 |
| 스레드/프로세스/asyncio CPU·I/O 비교 | [3-9 비교 실습](03-execution/09-benchmark.md) | 기존 실제 실험 192작업 검증. 준비 비용과 본 측정 구분 |

## 2. FastAPI와 동기/비동기

| 요청한 항목 | 읽을 단원 | 포함 여부와 보강 |
| --- | --- | --- |
| 원시 단일 서버·블로킹·스레드풀 | [4-1 작은 서버](04-fastapi/01-basic-server.md) | 기존 실제 HTTP 실험 있음 |
| def / async def / 안의 동기 코드 | [4-2 실행 경계](04-fastapi/02-def-async.md) | 기존 포함. 작업별 코드 배치와 공유 토큰 경쟁 보강 |
| boto3와 블로킹 SDK | [4-3](04-fastapi/03-blocking-sdk.md) | 기존 포함. read/close·GIL 해제와 루프 진행 구분 |
| LocalStack S3 동시 요청 10개 | [4-4 실제 S3 실습](04-fastapi/04-localstack.md) | 기존 180회 읽기 검증. 지연 주입과 실제 네트워크 구분 |
| uvicorn --workers / PID 분산 | [4-5 워커](04-fastapi/05-workers.md) | 기존 2워커 실제 HTTP 검증. 지속 연결과 새 연결 분리 |
| to_thread·스레드풀·max_pool_connections | [4-6 풀과 비동기 SDK](04-fastapi/06-pools.md), [7-4 취소](07-cache-timeouts/04-cancellation.md) | 기존 포함. 실제 구현의 보관 한도와 동시성 제한 구분 |
| aioboto3 | [4-6](04-fastapi/06-pools.md) | 기존 선택 기준에 async client/Body 수명 예시 추가. aioboto3 자체 실행은 미검증 |
| fork 이슈·자원 생성/종료 | [4-7 수명](04-fastapi/07-lifecycle.md) | 기존 포함. spawn/fork/forkserver·워커별 client 초기화 |

## 3. 공통편 위에 얹는 Python 항목

| 요청한 항목 | 읽을 단원 | 포함 여부와 보강 |
| --- | --- | --- |
| DB 풀 계산 | [5-8 풀 예산](05-database/08-pool-budget.md) | 기존 포함. Engine/Session 수명·배포 공존 예산 보강 |
| lru_cache / cachetools / 멀티프로세스 | [7-1 캐시](07-cache-timeouts/01-local-shared.md), [7-2 갱신](07-cache-timeouts/02-invalidation.md) | 기존 2프로세스 실험. TTLCache의 가짜 시계 경계 테스트 추가 |
| httpx / boto3 / DB / Uvicorn / LB timeout | [7-3 예산](07-cache-timeouts/03-timeout-budget.md) | 기존 포함. HTTPX·botocore 구체 설정의 시간 범위 보강 |
| asyncio.timeout·스레드 취소 | [7-4](07-cache-timeouts/04-cancellation.md) | 기존 실제 취소 후 스레드 잔존·종료 확인 |
| Uvicorn 직접 노출과 프록시 | [8-1](08-deployment/01-proxy.md) | 기존 포함. 플랫폼별 보호 책임과 신뢰 헤더/직접 접근 보강 |
| Docker CPU 제한·worker·os.cpu_count | [8-3](08-deployment/03-resources.md) | 기존 포함. affinity/cgroup 읽기 전용 점검 코드 추가 |
| logging·JSON·request-id | [9-1 로깅](09-observability/01-logging.md) | 기존 JSON 로그 실험 있음 |
| contextvars | [9-2](09-observability/02-contextvars.md) | 기존 task/to_thread/executor 검증. copy_context의 명시적 전파·역전파 한계 보강 |
| prometheus-client / OTel / Grafana | [9-3 신호](09-observability/03-signals.md), **[신규 9-7 연결 실습](09-observability/07-live-metrics.md)** | 기존 개념에 exporter·scrape 설정·대시보드 JSON·OTel 수집 경로 추가 |
| loop lag·토큰·RSS·boto3 pool | [9-4 지표](09-observability/04-bottleneck-metrics.md), [9-7](09-observability/07-live-metrics.md) | 기존 정의에 실행한 exporter 추가. boto3 호출 시간≠실제 풀 대기 |
| 풀 소진·루프 막힘→대시보드 | [9-5](09-observability/05-fault-lab.md), [9-7](09-observability/07-live-metrics.md) | 기존 저장 그래프에서 실시간 연결 절차로 확장. Grafana 실행 자체는 미검증 |
| py-spy / tracemalloc / memray | [9-6 프로파일링](09-observability/06-profiling.md) | 기존 tracemalloc 실행. attach/record/native 수집의 사용 형태·권한·한계 보강 |
| pytest / fixture / parametrize | [10-1](10-testing/01-pytest.md) | 기존 21개 테스트 있음 |
| pytest-asyncio / AnyIO | [10-2](10-testing/02-async-lifecycle.md), **[신규 10-7](10-testing/07-python-toolkit.md)** | 기존 pytest-asyncio에 AnyIO marker/backend 실제 예제 추가 |
| factory / polyfactory | [10-3](10-testing/03-factories.md), [10-7](10-testing/07-python-toolkit.md) | 기존 수동 factory에 polyfactory 실제 생성·경계값 override 추가 |
| moto / LocalStack / mock의 한계 | [10-4](10-testing/04-aws-doubles.md), [10-5](10-testing/05-test-layers.md), [10-7](10-testing/07-python-toolkit.md) | 기존 LocalStack에 moto S3 왕복·NoSuchKey 계약 테스트 추가 |
| 루프/스레드/worker/DB 병목 맞히기 | [11-4](11-performance/04-bottleneck-lab.md) | 기존 120초 × 3단계 실험. 네 병목별 반증 가능한 실험 카드 보강 |
| 우리 스택 동시 요청/처리량 계산 | [12-4](12-architecture/04-stack-limits.md) | 기존 자원별 계산. HTTP 진행·토큰·DB 점유·SDK 작업·RPS의 단위 분리 보강 |
| comprehension / generator / context manager | [13-2](13-coding/02-pythonic.md) | 기존 포함. 수명·일회 소비·자원 소유권·대안 비교 |
| 매일 15분 stdlib/FastAPI/Starlette 읽기 | [13-5](13-coding/05-reading.md) | 기존 5일 계획·실제 소스 확인. 다음날 재현 가능한 읽기 기록 보강 |

## 권장 진행 순서

3-5→3-7~3-9→4-1~4-7→5-8→7장→8-1·8-3→9장→10장→11-4→12-4→13-2·13-5로 읽습니다. 단원마다 본문의 퀴즈를 풀고 연결된 별도 해설을 확인하세요. 신규 두 편도 각각 5문항과 해설을 포함합니다.

## 실습 저장소와 확인 범위

- 공통편: [내 맘대로 팀 입사 교육과정](https://osoriandomori.github.io/posts/%EB%82%B4-%EB%A7%98%EB%8C%80%EB%A1%9C-%ED%8C%80-%EC%9E%85%EC%82%AC-%EA%B5%90%EC%9C%A1%EA%B3%BC%EC%A0%95/)의 페이지를 확인했습니다. 이번 대조의 상세 기준은 사용자가 메시지에 제공한 Python 목록입니다.
- 외부 실습 Repo: [OsoriAndOmori/developer-guide-python](https://github.com/OsoriAndOmori/developer-guide-python). 2026-10-06 확인한 `main` revision `f8432c36095da3209beb6af1b0308d1838e3b42f`의 tree에는 README.md만 있었습니다. 나중에 파일이 추가될 수 있습니다. 존재하지 않는 실습 경로를 추측해 연결하지 않았습니다.
- 이번 실행: **7개 테스트 통과**, botocore deprecation 경고 11건. [JUnit](results/python-track-2026-10-06.xml), [실행 범위](results/README.md).
- Prometheus/Grafana/OTel 전체 배포, aioboto3, py-spy, memray는 이번 실행 검증 범위가 아닙니다. 기존 실행 결과·새 예제·독자 연결 과제를 각각 구분했습니다.
