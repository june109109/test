# 3-7. 코루틴과 이벤트루프 막힘

[목차](../README.md) · [이전](06-strategies.md) · [정답·해설](07-coroutines-answers.md)

예상 55분. 목표: coroutine·Task·Future를 구분하고, await와 일반 함수 호출의 실행 위치를 추적하며, 루프 막힘을 고치는 선택을 비교합니다.

## 1. async 함수는 호출만으로 끝까지 실행되지 않는다

일반적으로 `async def` 함수를 호출하면 코루틴 객체를 얻습니다. `await`하거나 task로 스케줄해야 실행됩니다. coroutine은 일시 중단·재개 가능한 실행을 표현하고, Task는 코루틴을 이벤트루프에서 실행하도록 관리하는 객체입니다. Future는 나중에 준비될 결과를 나타내는 저수준 추상입니다.

단순한 `await a(); await b()`는 a가 끝난 뒤 b를 실행하는 순차 관계입니다. 독립 작업을 겹치려면 task를 만들거나 `gather`·`TaskGroup` 같은 방식으로 함께 실행할 수 있습니다. 하지만 의존성이 있는 두 작업을 억지로 병행해서는 안 됩니다.

## 2. 협력적 스케줄링

한 이벤트루프는 한 번에 한 task의 Python 코드를 진행합니다. task가 미완료 awaitable을 기다릴 때 다른 task·callback·I/O가 실행될 수 있습니다. `await`라는 글자만 있는 것이 아니라 실제로 양보가 일어나야 합니다.

```python
import asyncio
import time

async def bad_wait():
    time.sleep(0.2)  # 루프 스레드에서 일반 함수가 직접 실행됨

async def cooperative_wait():
    await asyncio.sleep(0.2)  # task는 대기, 루프는 다른 작업 진행 가능

async def offloaded_wait():
    await asyncio.to_thread(time.sleep, 0.2)  # 동기 함수를 별도 스레드로
```

위는 함수 정의 예시입니다. `async def`로 감싸도 `time.sleep`, 동기 HTTP 요청, 긴 CPU 계산이 자동으로 다른 곳에서 실행되는 것은 아닙니다. 해당 함수가 `await`를 지원하지 않는다면 억지로 `await`를 붙이는 것도 해결책이 아닙니다.

## 3. CPU 계산에서 await를 어디에 둘까

긴 루프 중간에 `await asyncio.sleep(0)`을 넣으면 다른 task가 실행할 기회를 얻도록 할 수 있습니다. 응답성을 개선할 수 있지만 계산이 여러 코어로 병렬화되거나 총 계산량이 줄어드는 것은 아닙니다. 너무 자주 양보하면 오버헤드가 늘고 너무 드물면 지연이 큽니다.

| 방법 | 이익 | 감수할 비용 |
| --- | --- | --- |
| 비동기 API 사용 | 대기를 루프에 자연스럽게 통합 | 라이브러리·수명·취소 의미 학습 |
| to_thread·스레드풀 | 동기 I/O 재사용, 루프 보호 | 풀 한도, 동시 안전성, 강제 취소 불가 |
| 프로세스 계산 | 순수 Python 계산 병렬화 가능 | 직렬화·시작·메모리·결과 전달 |
| 작은 계산 조각과 양보 | UI·타이머 응답성 | 분할 구현·양보 비용, 병렬성 없음 |

순수 Python CPU를 to_thread로 옮기면 이벤트루프를 직접 길게 점유하는 것보다는 나을 수 있지만 GIL 경쟁이 남아 지연·처리량을 보장하지 않습니다. 많은 CPU 작업은 별도의 실행 예산이 필요합니다.

## 4. await 전후에도 상태가 바뀐다

단일 스레드라도 task A가 재고를 확인하고 await한 뒤 차감하는 사이 task B가 같은 재고를 바꿀 수 있습니다. 데이터 경쟁을 ‘동시에 두 CPU가 쓰는 일’로만 보면 이 논리적 경쟁을 놓칩니다. 필요한 원자성·소유자·비동기 락·DB 트랜잭션 등으로 계약을 지켜야 합니다.

취소는 보통 다음 적절한 실행 지점에 `CancelledError`를 전달합니다. task가 동기 계산·호출로 루프를 막으면 timeout·취소를 처리할 기회도 늦어집니다. `finally`로 필요한 정리를 수행하고 취소를 함부로 삼키지 않습니다. `to_thread` 작업을 기다리는 task 취소는 실행 중인 스레드 함수의 즉시 중단을 의미하지 않습니다.

## 관찰 과제

위 세 대기 함수를 heartbeat task와 함께 실행하는 실험을 설계하세요. heartbeat는 일정 간격으로 시간을 기록하고 실제 간격이 벌어진 정도를 봅니다. CPU 사용률만으로 루프 막힘을 찾기 어려운 이유도 설명하세요. `time.sleep`은 CPU를 많이 쓰지 않지만 그 스레드는 멈춥니다. 이 특정 heartbeat 실험은 아직 실행하지 않았으며, 3-9에서는 전체 작업 시간 비교를 실제로 실행합니다.

### Python 트랙 보강: coroutine·Task·취소의 경계

`coro = work()`는 coroutine 객체를 만들 뿐 본문을 실행하지 않습니다. `await work()`는 현재 task의 흐름에서 실행하고, `asyncio.create_task(work())`는 별도 task로 예약합니다. CPU 병렬 실행을 만드는 기능은 아닙니다. 여러 작업을 하나의 요청 수명에 묶을 때는 Python 3.11+의 TaskGroup을 후보로 비교하세요. 자식 실패 시 다른 자식의 취소·종료를 기다리는 계약을 이해해야 합니다.

`await`가 보인다는 이유만으로 루프가 양보된다고 추정하지 않습니다. 이미 완료된 awaitable, await 이전의 JSON 변환·압축·동기 SDK도 확인하세요. [3-5의2×2표](05-sync-async.md)로 ‘누가 기다리는가’를 먼저 정하고, [7-4](../07-cache-timeouts/04-cancellation.md)에서 응답 취소와 실제 작업 종료를 분리합니다.

## 퀴즈

Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 권장 통과 8점.

### Q1
`async def` 함수 안에서 일반 동기 함수를 호출하면 자동으로 스레드풀에 넘어가나요?

### Q2
`await a(); await b()`는 a와 b의 병행 실행을 자동 보장하나요?

### Q3
`await asyncio.sleep(0)`을 계산 중간에 넣어 얻는 것과 얻지 못하는 것을 설명하세요.

### Q4
이벤트루프가 하나의 스레드라면 재고 확인과 차감 사이에 await가 있어도 안전한가요? 이유를 쓰세요.

### Q5
동기 SDK를 호출하는 async 함수가 모든 요청을 늦춥니다. 두 해결 후보를 비교하고 한도·취소·검증 계획을 적으세요.

## 출처

2026-10-01 확인.

- [Python 3.12 asyncio task 문서](https://github.com/python/cpython/blob/3.12/Doc/library/asyncio-task.rst): awaitables·task·sleep·to_thread·취소.
- [Python 3.12 concurrent.futures](https://github.com/python/cpython/blob/3.12/Doc/library/concurrent.futures.rst): 실행 중 작업과 Future 취소의 구분.
