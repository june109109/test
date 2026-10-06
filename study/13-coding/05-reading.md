# 13-5. 매일 15분 코드 읽기

[목차](../README.md) · [정답·해설](05-reading-answers.md)

예상 첫 학습45분 + 이후 하루15분. 목표: 읽은 줄 수 대신 질문·예측·검증으로 라이브러리 이해를 쌓습니다.

## 1. 질문 하나로 시작

큰 저장소를 처음부터 끝까지 읽기보다 ‘FastAPI의 def는 어디서 스레드로 넘어가는가’, ‘with에서 예외가 나면 generator는 어떻게 정리되는가’처럼 관찰 가능한 질문을 정합니다. 문서의 계약→호출 경로→핵심 구현→작은 검증 순서로 연결합니다.

| 시간 | 활동 | 남길 것 |
| --- | --- | --- |
| 0~3분 | 버전·질문·예상 동작 | 틀릴 수 있는 예측 한 문장 |
| 3~10분 | 호출자·피호출자·분기 탐색 | 3~5개 함수의 경로 |
| 10~13분 | 작은 사례/기존 테스트 확인 | 예측과 관찰 차이 |
| 13~15분 | 정리 | 업무 적용·미해결 질문 |

15분은 습관의 시간 제한이지 모든 코드를 이해하는 보장이 아닙니다. 모르는 내부 이름에 오래 막히면 질문 범위를 줄입니다.

## 2. 실제 확인한 호출 경로

2026-10-02 설치된 FastAPI0.141.1·Starlette1.6.0·AnyIO4.14.2의 소스를 inspect로 읽었습니다.

```text
FastAPI routing.run_endpoint_function
  is_coroutine=True → await dependant.call(**values)
  is_coroutine=False → await run_in_threadpool(dependant.call, **values)
Starlette concurrency.run_in_threadpool
  functools.partial로 인자 묶기
  → await anyio.to_thread.run_sync(func)
```

이 경로는4-2의실행 위치 실험과 맞습니다. endpoint 안에서 사용자가 직접 호출한 일반 helper는 이 분기를 다시 통과하지 않으므로 자동 offload되지 않습니다. middleware·의존성·background 작업은 각각 별도의 호출 경로를 찾아야 합니다.

다음 읽기 명령은 버전과 함수의 실제 소스를 출력합니다. 사용자 코드/환경 전체를 덤프하는 명령이 아닙니다.

```bash
python3 - <<'PYCODE'
import inspect
from importlib.metadata import version
from fastapi.routing import run_endpoint_function
from starlette.concurrency import run_in_threadpool
print(version('fastapi'), version('starlette'), version('anyio'))
print(inspect.getsource(run_endpoint_function))
print(inspect.getsource(run_in_threadpool))
PYCODE
```

## 3. 5일 읽기 계획

| 날 | 질문 | 파일/대상 | 작은 확인 |
| --- | --- | --- | --- |
| 1 | def endpoint는 어디서 실행? | FastAPI routing | 4-2의thread ID |
| 2 | 인자 있는 함수는 어떻게 offload? | Starlette concurrency | partial·AnyIO 호출 읽기 |
| 3 | with 예외는 어떻게 전달? | contextlib._GeneratorContextManager.__exit__ | 예외 전파·finally 사례 |
| 4 | LRU miss는 한 번만 계산? | functools 문서와CPython 구현 | 중복 miss 가능 조건 예측 |
| 5 | 풀 제한은 어느 객체가 담당? | AnyIO limiter·설치 버전 문서 | 9-5의 borrowed/total대조 |

1~2일의 소스 경로와3일의 contextlib 소스는 직접 읽었습니다. 모든 5일 확장 과제를 실행한 것은 아닙니다. C 구현 builtin은 inspect.getsource가 되지 않을 수 있으므로 해당 버전의 소스 저장소·문서·테스트를 찾습니다.

## 4. 읽기를 업무에 적용

내부 구현은 버전에 따라 바뀔 수 있습니다. 문서화된 공개 계약과 우연한 내부 동작을 구분하고, 내부 함수/속성에 의존한다면 업그레이드 위험과 회귀검사를 기록합니다. 단순히 유명 라이브러리가 그렇게 했다는 이유로 내 코드에 복사하지 않습니다.

코드를 읽고 틀린 추측 하나를 고쳤거나 장애 가설 하나를 검증했다면 충분한 산출물입니다. 읽은 줄 수·파일 수보다 정확한 예측과 적용을 성장의 신호로 삼습니다.1-5의학습/버리기와1-8의업무 적용으로 다시 연결됩니다.

## 5. 적용 과제

‘`async def` 안의 일반 함수가 자동으로 스레드에서 실행된다’라는 주장을 소스·실험으로 검토하는15분 노트를 쓰세요. 출발 질문, 설치 버전, 호출 경로, 반증, 업무 변경 한 가지를 포함합니다.

### Python 트랙 보강: 다음날 재현 가능한 읽기 기록

매일 `버전/commit → 질문 → 호출자 → 분기 조건 → 피호출자 → 관찰 → 업무 적용` 일곱 항목을 남기세요. 예: ‘직접 호출한 sync helper는 FastAPI의run_endpoint_function 분기를 다시 통과하지 않는다’라는 예측을4-2의thread ID로 확인합니다.

사용자가 제공한 외부 실습 저장소는2026-10-06에 확인한main revision에서README만 있었습니다. 향후 코드가 추가되면 파일 경로와revision을 기록하고, 이 교재의 기존 실험과 입력·계측 경계를 맞춰 비교하세요. 저장소 이름만 같다고 실행 결과가 같다고 보지 않습니다. 전체 연결은 [Python 트랙 안내](../PYTHON_FASTAPI_TRACK.md)에 있습니다.

## 퀴즈

### Q1

라이브러리의 현재 내부 구현은 모든 버전의 공개 계약과 같은가?

### Q2

C 구현 builtin도 inspect.getsource로 항상 읽을 수 있는가?

### Q3

확인한 FastAPI def 경로의 두 단계 위임을 설명하라.

### Q4

코드 읽기 노트에 버전과 예측을 남기는 이유는?

### Q5

15분 안에 하나의 실행 경계 주장을 검증하는 노트를 설계하라.

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- 직접 확인: 설치된FastAPI0.141.1 `routing.run_endpoint_function`, Starlette1.6.0 `concurrency.run_in_threadpool`, CPython3.12.14 `contextlib._GeneratorContextManager.__exit__`.
- [PEP20](https://peps.python.org/pep-0020/), [Python inspect](https://docs.python.org/3/library/inspect.html) — 참고 계약과 도구.

확인일: 2026-10-02. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
