# 9-2. contextvars와 실행 경계

[목차](../README.md) · [정답·해설](02-contextvars-answers.md)

예상 50분. 목표: task별 값의 분리와 복사 시점을 이해하고, thread/process 경계를 직접 확인합니다.

## 1. 전역 변수와 thread-local의 한계

요청 ID를 모듈 전역 변수 하나에 넣으면 동시 요청이 덮어씁니다. 이벤트루프는 같은 스레드에서 여러 task를 실행하므로 thread-local도 요청을 구분하지 못할 수 있습니다. ContextVar는 현재 실행 context에 연결된 값을 조회합니다.

```python
request_id = ContextVar('request_id', default=None)

token = request_id.set('request-A')
try:
    await handle_request()
finally:
    request_id.reset(token)
```

설명용 부분 코드입니다. reset은 항상 None으로 바꾸는 것이 아니라 이전 context 값을 복원합니다. 중첩 호출에서 token을 보관하는 이유입니다.

## 2. 전파 규칙

asyncio task는 생성 시점의 context를 복사하는 것이 기본입니다. 이후 부모 ContextVar를 다시 set한다고 이미 만든 task가 자동으로 같은 값으로 바뀌지 않습니다. 복사는 가변 객체까지 깊은 복사한다는 뜻이 아니므로 dict 같은 값을 공유·수정하면 별도 문제가 생길 수 있습니다.

| 경계 | 일반적인 동작 | 설계 포인트 |
| --- | --- | --- |
| 같은 task의 await | 같은 context 흐름 | set/reset 범위 |
| 새 asyncio task | 생성 시 context 복사 | 생성 시점과 background 수명 |
| asyncio.to_thread | 현재 context 전파 | 변경의 부모 역전파는 아님 |
| 기본 run_in_executor | 자동 context 전파를 가정하지 않음 | 필요하면 명시적 copy_context |
| 별도 프로세스·HTTP·큐 | 요청 context 자동 전달 아님 | 명시적 metadata/헤더 |

## 3. 실제 실험

[실행 코드](../labs/observability.py), [결과](../results/observability-2026-10-02.json).

```bash
python3 study/labs/observability.py --output /tmp/observe-new.json
```

AnyIO가 필요하며 4장의 의존성에 포함됩니다. 서로 다른 task 두 개를 동시에 실행했습니다.

| 요청 | task에서 값 | to_thread | run_in_executor |
| --- | --- | --- | --- |
| A | request-A | request-A | null |
| B | request-B | request-B | null |

로그 두 개도 각각의 ID를 유지했고, reset 후 부모 context는 null이었습니다. 이번 환경의 표준 asyncio 경계 결과이며 다른 프레임워크가 명시적 전파를 추가하는 경우는 별도로 확인해야 합니다.

## 4. 적용 과제

요청에서 background task를 만들고 응답을 끝낸 뒤 그 task가 계속 실행될 때 ID를 어떻게 표현할지 결정하세요. 원 요청 ID를 남길지 새 job_id를 만들지, task 생성 당시의 인증 정보를 나중에 그대로 신뢰해도 되는지도 구분하세요.

### Python 트랙 보강: 명시적으로 executor에 전파하기

```python
# asyncio 문맥의 설명용 조각
ctx = contextvars.copy_context()
result = await loop.run_in_executor(None, ctx.run, blocking_function)
```

각 제출마다 새 context를 복사합니다. 같은 Context 객체를 동시에 여러 스레드에서 enter하려고 재사용하지 않습니다. `asyncio.to_thread`는 기본적으로 context 전파를 제공하지만 스레드 안의 set이 부모 task로 자동 역전파되지는 않습니다. HTTP/메시지/프로세스로 넘어갈 때는 별도 헤더/metadata로 전달해야 합니다. contextvars는 인증 정보의 신뢰성이나 mutable 값의 깊은 복사를 보장하지 않습니다.

## 퀴즈

### Q1

같은 이벤트루프의 동시 요청을 thread-local 하나로 구분할 수 있는가?

### Q2

ContextVar.reset(token)은 항상 None을 저장하는가?

### Q3

새 task 생성 후 부모가 set한 값이 자식에 자동 반영되지 않는 이유는?

### Q4

to_thread와 기본 run_in_executor의 관찰 결과 차이는?

### Q5

HTTP 호출과 background job으로 이어지는 request-id 전파·정리를 설계하라.

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- [Python contextvars](https://docs.python.org/3/library/contextvars.html).
- [asyncio.to_thread](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread). 실험 결과와 라이브러리별 추가 전파를 구분합니다.

확인일: 2026-10-02. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
