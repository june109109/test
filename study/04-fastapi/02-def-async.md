# 4-2. FastAPI의 def와 async def

[목차](../README.md) · [이전](01-basic-server.md) · [정답·해설](02-def-async-answers.md)

예상 65분. 목표: FastAPI가 호출하는 경계와 직접 호출을 구분하고, 실행 위치와 대기 방식으로 경로 함수를 선택하며, 실제 테스트의 범위를 설명합니다.

## 1. FastAPI가 대신 실행하는 함수

FastAPI는 요청에 맞는 경로 함수를 찾고 의존성을 해결한 뒤 실행합니다. 일반적인 실행 규칙은 다음과 같습니다. 순수 Python의 모든 함수 호출 규칙을 바꾸는 마법은 아닙니다.

| 함수의 위치 | 선언 | 일반적인 실행 위치 |
| --- | --- | --- |
| FastAPI 경로 함수 | `async def` | 이벤트루프 스레드에서 await |
| FastAPI 경로 함수 | `def` | AnyIO 기반 스레드 실행으로 오프로딩 |
| FastAPI `Depends`로 호출하는 의존성 | `def` | 스레드 실행으로 오프로딩 |
| FastAPI `Depends`로 호출하는 의존성 | `async def` | 비동기 실행 |
| 코드에서 직접 부른 일반 helper | `def` | 호출한 스레드에서 즉시 실행 |

`Depends`는 FastAPI가 함수 인자를 준비하기 위해 선언된 다른 함수를 실행하는 장치입니다. 함수를 ‘의존성’이라고 이름 붙여도 직접 `helper()`로 호출하면 자동 오프로딩되지 않습니다. generator 의존성의 초기화·종료 등 세부 수명은 추가로 확인해야 합니다.

## 2. 네 가지 경로의 차이

| 경로 | 수행 | 예상 |
| --- | --- | --- |
| async-blocking | async 함수 안에서 `time.sleep(0.05)` | 루프 스레드가 막힘 |
| sync | def 경로 함수에서 `time.sleep(0.05)` | 스레드에서 대기, 루프는 진행 가능 |
| async-io | async 함수에서 `await asyncio.sleep(0.05)` | task 대기, 루프는 진행 가능 |
| async-thread | async 함수에서 `await anyio.to_thread.run_sync(...)` | 명시적인 스레드 오프로딩 |

sleep은 이 실험에서 **대기 방식 비교를 위한 모형**입니다. 실제 S3·DB I/O의 속도나 장애를 측정하지 않습니다. 3-9의 실제 소켓 I/O 실험과 목적이 다릅니다.

## 3. 어떤 것을 선택할까

| 선택 | 좋은 조건 | 얻는 이익 | 비용 |
| --- | --- | --- | --- |
| def 경로 | 주된 작업이 동기 I/O | 기존 코드의 단순한 흐름 유지 | 스레드 토큰·대기·수명 관리 |
| async 경로 + 비동기 API | 라이브러리와 호출 사슬이 비동기 | 많은 대기 관리·작업 조합 | 블로킹 혼입·취소·세션 관리 |
| async 경로 + 일부 오프로딩 | 비동기 흐름 중 동기 호출 일부 | 기존 라이브러리 재사용 | 실행 경계·풀·취소 비용 |
| CPU 작업 별도 실행 | 계산이 크고 병렬화 가치가 있음 | 루프 보호·계산 용량 | IPC·작업 큐·결과·실패 계약 |

작은 상수 반환 때문에 무조건 def를 선택할 이유는 없습니다. 반대로 async라는 이름만 보고 동기 SDK를 그대로 넣으면 루프를 막을 수 있습니다. CPU 작업은 def 스레드풀로 바꿨다는 사실만으로 GIL 제약이 없어지지 않습니다.

## 4. 스레드 제한의 의미

확인한 Starlette 문서는 `anyio.to_thread.run_sync`와 기본 40 tokens를 설명합니다. 이 실행 환경에서도 기본 limiter가 40임을 관찰했습니다. 이는 모든 서비스·버전의 영원한 상수가 아니며 배포 환경의 설정을 확인해야 합니다.

동기 의존성·일부 파일 처리·다른 AnyIO 호출도 같은 제한을 사용할 수 있습니다. ‘40=프로세스의 모든 스레드 수’ 또는 ‘asyncio.to_thread의 최대 수’라고 바꾸어 말하면 안 됩니다. FastAPI 워커가 여러 개면 일반적으로 각 프로세스의 실행·풀 상태도 따로 존재합니다. 자세한 풀 관계는 4-6에서 다룹니다.

## 5. 실습 준비·실행

[실습 코드](../labs/fastapi_boundaries.py)는 Python 3.11 이상과 FastAPI·AnyIO·HTTPX를 사용합니다. 실행 확인 환경의 버전은 [의존성 목록](../labs/requirements-fastapi.txt)과 [결과 JSON](../results/fastapi-boundaries-2026-10-01.json)에 있습니다.

현재 환경에 해당 패키지가 이미 있어 추가 설치 없이 검증했습니다. 다른 환경에서는 별도의 가상환경에 목록을 설치하세요. 이 목록은 확인한 직접 패키지를 고정한 것이며 모든 전이 의존성의 완전한 lockfile은 아닙니다.

```bash
cd /workspace/test
python3 study/labs/fastapi_boundaries.py --output /tmp/fastapi-boundaries-my-run.json
```

HTTPX의 ASGITransport로 앱을 같은 프로세스에서 호출합니다. **실제 TCP·TLS·Uvicorn·여러 워커를 거치지 않습니다.** FastAPI의 실행 경계를 관찰하는 통합 실험이지 네트워크 부하 시험이 아닙니다. lifespan이 필요한 앱을 이 방식으로 시험한다면 별도 수명 관리가 필요하지만 이 예제는 그런 자원을 만들지 않습니다.

## 6. 실제 결과

2026-10-01, CPython 3.12.14. FastAPI 0.141.1, Starlette 1.6.0, AnyIO 4.14.2, HTTPX 0.28.1. 경로마다 동시 요청 10개, 대기 50ms, 3회 중앙값입니다.

| 경로 | 10개 완료 중앙값 | 최고 활성 handler 본문 수 | 실제 업무 코드 위치 |
| --- | ---: | ---: | --- |
| async-blocking | 0.508293초 | 1 | 루프 스레드 |
| sync | 0.059890초 | 10 | 다른 스레드 |
| async-io | 0.054718초 | 10 | 루프 스레드, 대기는 양보 |
| async-thread | 0.057544초 | 10 | 업무를 다른 스레드로 이동 |

120개 측정 응답의 성공·실행 스레드·handler 겹침을 검증했습니다. 추가 의존성 경로에서 `def Depends`는 다른 스레드, async 경로와 직접 helper는 루프 스레드에서 실행되는 것도 확인했습니다.

‘활성 handler’는 본문에 진입한 뒤 아직 끝나지 않은 수입니다. await로 대기하는 task도 포함되므로 동시에 CPU를 실행한 수와 같지 않습니다. 약 0.5초와 0.05초의 차이는 대기 방식에 부합하지만 세 비차단 경로 사이의 작은 숫자 차이로 우열을 일반화하지 않습니다.

## 적용 과제

자신의 API에서 경로 함수→의존성→helper→SDK의 호출 사슬을 그리세요. 각 경계에 호출자 스레드·블로킹 가능성·오프로딩 여부를 표시합니다. 함수 이름과 async 선언만 보고 SDK가 비동기라고 추측하지 않습니다.

### Python 트랙 보강: 코드 배치 결정표

| 처리 내용 | 출발점 | 반드시 확인할 비용 |
| --- | --- | --- |
| httpx.AsyncClient 등 async I/O | async def + await | 풀 대기·deadline·client 수명 |
| 동기 SDK 중심의 짧은 경로 | def 경로 | 공유 AnyIO 토큰·하류 한도 |
| async I/O와 일부 boto3 혼합 | async def에서 명시적 오프로딩 | 대기 취소 후 잔여 작업·별도 executor 여부 |
| 긴 Python CPU 계산 | 별도 프로세스/작업 서비스 검토 | 직렬화·결과 전달·작업 상태·자원 제한 |

Starlette/AnyIO의 통상 기본 40토큰은 버전별로 확인하며 모든 스레드의 총수나 서버 전체 한도로 읽지 않습니다. 같은 limiter를 쓰는 동기 dependency·경로 등이 경쟁할 수 있습니다. 워커2개는 별도 limiter2개이므로 하류 부하는 합산됩니다. 토큰을 늘리기 전에 제출 대기와 실제 SDK 시간을 나누어 봅니다. [9-7](../09-observability/07-live-metrics.md)에서 토큰2개에 요청8개를 보내는 관측 절차를 제공합니다.

## 퀴즈

Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 권장 통과 8점.

### Q1
async 경로 안에서 `def helper()`를 직접 부르면 FastAPI가 자동으로 스레드에 보내나요?

### Q2
기본 AnyIO limiter가 40이면 프로세스 전체의 모든 스레드 수가 정확히 40인가요?

### Q3
동기 SDK를 주로 사용하는 경로에 def를 쓰는 이익과 비용을 설명하세요.

### Q4
ASGITransport 실험으로 확인한 것 두 가지와 확인하지 못한 것 두 가지를 적으세요.

### Q5
async 경로에 동기 SDK 호출이 있고 동시 요청에서 전체가 느려집니다. 호출 사슬 진단과 대안, 자원 한도, 검증 지표를 제시하세요.

## 출처·실행 근거

2026-10-01 확인. 문서 기본 브랜치와 설치 버전은 이후 달라질 수 있어 실행 버전을 별도로 기록했습니다.

- [FastAPI 공식 async 문서](https://github.com/fastapi/fastapi/blob/master/docs/en/docs/async.md): `Path operation functions`, `Dependencies`, `Other utility functions`.
- [Starlette Thread Pool](https://github.com/Kludex/starlette/blob/main/docs/threadpool.md): AnyIO 실행·공유 token 제한.
- [실습 코드](../labs/fastapi_boundaries.py), [원본 결과](../results/fastapi-boundaries-2026-10-01.json).
