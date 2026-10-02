# 7-4. 취소 전파와 끝나지 않은 스레드

[목차](../README.md) · [정답·해설](04-cancellation-answers.md)

예상 55분. 목표: await 종료·task 취소·실제 작업 종료를 구분하고, 취소 후 자원을 안전하게 정리합니다.

## 1. 취소는 강제 종료 버튼이 아니다

asyncio task에 취소를 요청하면 코루틴이 다음 취소 가능한 지점에서 `CancelledError`를 받습니다. 모든 코드가 즉시 멈추는 인터럽트가 아닙니다. CPU 루프나 동기 I/O가 이벤트루프 스레드를 붙잡고 있으면 다른 task와 timeout 처리도 지연됩니다.

```python
async def work():
    resource = await acquire_resource()  # 설명용 함수
    try:
        return await use_resource(resource)
    finally:
        await release_resource(resource)
```

finally에 정리를 두는 패턴은 유용하지만 정리 자체도 실패·취소·시간 초과할 수 있습니다. 라이브러리가 제공하는 context manager와 명시적 종료 계약을 확인합니다. `CancelledError`를 잡았다면 정리 후 다시 전달하는 것이 일반적이며 이유 없이 삼키면 timeout·TaskGroup 등의 구조적 동시성이 깨질 수 있습니다.

## 2. asyncio.timeout의 바깥에서 TimeoutError 처리

```python
try:
    async with asyncio.timeout(1.0):
        await external_call()
except TimeoutError:
    record_timeout()
```

이 부분 예제에서 timeout context는 내부 취소를 바깥의 TimeoutError로 바꿉니다. 1초는 경성 실시간 실행 보장이 아니며 루프가 진행 가능해야 합니다. `wait_for`도 취소 정리를 기다리면서 지정 시간보다 오래 걸릴 수 있습니다.

`shield`는 안쪽 task에 특정 외부 취소가 전달되지 않게 할 수 있지만, 호출자의 취소 자체를 없애거나 작업의 안전한 수명 관리를 자동 제공하지 않습니다. 어떤 작업을 누가 끝까지 관찰·정리할지 필요합니다.

## 3. 스레드 오프로딩의 실제 결과

[코드](../labs/cache_cancellation.py), [JSON](../results/cache-cancellation-2026-10-01.json). 실행 방법은 [7-1](01-local-shared.md)에 있습니다.

실험은 `asyncio.to_thread`로 블로킹 함수를 실행하고, 실제 시작을 확인한 뒤 20ms timeout으로 await합니다. 함수는 threading.Event를 기다리므로 timeout 후에도 살아 있는지 확실히 관찰할 수 있습니다.

| 시점 | asyncio task | 스레드의 함수 |
| --- | --- | --- |
| 시작 확인 후 | 실행/대기 중 | Event 대기 중 |
| timeout 발생 후 | cancelled=True | 여전히 실행 중 |
| 명시적으로 Event 해제 후 | 취소 상태 유지 | 종료 확인 |

2026-10-01 직접 확인했습니다. 종료 시 Event를 해제하고 스레드가 끝난 것을 확인합니다. executor 스레드를 남겨 둔 채 ‘응답이 끝났으니 완료’로 처리하지 않습니다.

## 4. 연결·동시성 제한이 깨질 수 있는 지점

```text
앱 semaphore 획득 → to_thread 호출 → await timeout
  → 앱 finally에서 semaphore 반환
  → 그러나 기존 스레드의 네트워크 호출은 계속 진행
  → 새 요청이 입장하면 실제 실행 작업 수가 설정값을 넘을 수 있음
```

해결은 단순히 timeout을 늘리는 것이 아닙니다. 블로킹 SDK의 자체 네트워크 timeout, 실제 작업 수명에 묶인 admission, 제한된 executor/큐, 지원되는 협력 취소를 설계합니다. 강제 중단이 꼭 필요하면 프로세스 격리가 대안이지만 프로세스를 죽여도 외부 시스템에 이미 반영한 부작용은 돌아오지 않습니다.

AnyIO `to_thread.run_sync`의 취소 처리·abandon 옵션과 asyncio.to_thread를 같은 의미로 취급하지 않습니다. 호출자가 기다림을 포기하는 것과 실행 중 스레드를 중단시키는 것은 다릅니다. 사용하는 버전·기본값을 확인하세요.

## 5. 적용 과제

S3 업로드를 스레드로 실행하고 요청은 1초 만에 timeout되었는데 2초 뒤 업로드가 끝났습니다. 사용자에게 상태를 어떻게 표시하고 중복 재시도·남은 작업·자원 한도를 어떻게 관리할지 설계하세요.

## 퀴즈

### Q1

await하는 task가 cancelled이면 그 안에서 시작한 스레드 함수도 종료되었는가?

### Q2

이벤트루프를 동기 CPU 루프로 막아도 timeout은 정확히 제시간에 실행되는가?

### Q3

CancelledError를 이유 없이 삼키면 안 되는 이유는?

### Q4

await timeout 후 semaphore를 반환할 때 실제 동시성 한도가 깨질 수 있는 이유는?

### Q5

요청 timeout 후에도 업로드가 계속되는 시스템의 취소·상태·자원 관리를 설계하라.

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- [Python asyncio task·취소·to_thread](https://docs.python.org/3/library/asyncio-task.html).
- [AnyIO threads](https://anyio.readthedocs.io/en/stable/threads.html) — 다른 취소 계약을 비교하는 후속 읽기.
- 실험은 표준 asyncio.to_thread이며 AnyIO 스레드 취소를 직접 비교 실행한 것은 아닙니다.

확인일: 2026-10-01. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
