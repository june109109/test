# 4-3. async 안의 동기 SDK

[목차](../README.md) · [이전](02-def-async.md) · [정답·해설](03-blocking-sdk-answers.md)

예상 50분. 목표: SDK 이름이나 async 선언 대신 실제 블로킹 구간을 찾고, 오프로딩 범위·응답 스트림·취소·클라이언트 수명을 설계합니다.

## 1. boto3 호출에 await를 붙이면 해결될까

boto3의 일반 client 호출은 동기 API입니다. `await s3.get_object(...)`라고 쓰면 호출 자체가 먼저 현재 스레드에서 실행되고, 반환한 일반 dict는 await 대상이 아니어서 오류가 날 수 있습니다. `async def` 함수에 넣는 것만으로 동작이 비동기로 바뀌지 않습니다.

S3의 `get_object`는 응답 메타정보와 스트리밍 본문을 제공합니다. 요청을 보내는 부분뿐 아니라 **본문을 읽는 부분도** 블로킹될 수 있습니다. 헤더만 스레드에서 받고 루프 스레드에서 `.read()`를 수행하면 문제의 일부가 남습니다.

## 2. 실행 위치를 분명하게 만들기

다음은 설명용 함수 조각입니다. `client`는 프로세스 수명에 맞게 안전하게 준비한 boto3 client, `bucket`·`key`는 허용된 대상이라고 가정합니다.

```python
import asyncio

def read_small_object(client, bucket, key):
    response = client.get_object(Bucket=bucket, Key=key)
    body = response["Body"]
    try:
        return body.read()
    finally:
        body.close()

async def load_object(client, bucket, key):
    return await asyncio.to_thread(read_small_object, client, bucket, key)
```

요청·본문 읽기·정리를 같은 동기 작업으로 묶었습니다. 작은 객체의 학습용 방식이며 큰 객체 전체를 메모리에 읽는 것은 별도의 문제입니다. 큰 파일은 chunk 단위 처리·응답 스트리밍·동시성·메모리·연결 점유 수명을 함께 설계해야 합니다.

FastAPI/Starlette의 AnyIO 작업 제한과 맞추려면 `anyio.to_thread.run_sync` 또는 프레임워크가 제공하는 적절한 오프로딩 함수를 고려할 수 있습니다. `asyncio.to_thread`와 AnyIO 실행이 같은 한도라고 가정하지 않습니다.

## 3. 세 선택의 이득과 비용

| 선택 | 이익 | 비용·주의 |
| --- | --- | --- |
| 경로 자체를 def로 | 기존 동기 흐름을 쉽게 유지 | 경로 실행 동안 스레드 점유, 비동기 흐름 혼합 제약 |
| async 경로에서 동기 작업만 오프로딩 | 나머지 비동기 작업과 조합 | 작업 경계·풀·취소·SDK 안전성 관리 |
| 검증된 비동기 SDK로 교체 | 대기를 루프에서 관리 | API·버전 호환·라이프사이클·취소·패키지 지원 확인 |

aioboto3 같은 패키지는 후보이지만 boto3에 await만 붙인 것과 다릅니다. async context manager, 세션·클라이언트 수명, underlying botocore와의 버전 조합을 확인해야 합니다. 성능은 네트워크·객체 크기·하류 한도까지 포함해 비교합니다.

## 4. thread-safe의 범위를 읽기

boto3 공식 문서는 client가 일반적으로 thread-safe라고 설명하되 조건을 붙입니다. client metadata를 동시에 변경하거나 custom event hook을 추가한 경우에는 별도 검토가 필요합니다. Session·Resource를 client와 같은 방식으로 공유해도 된다고 일반화하지 않습니다. client는 프로세스 사이에 공유하지 않습니다.

매 요청·스레드에서 공유 기본 Session으로 client를 새로 만드는 대신, 해당 프로세스에서 Session과 client를 명시적으로 초기화한 뒤 문서의 허용 조건에 맞게 공유하는 설계를 고려하세요. 워커 수가 늘면 client·연결 풀·메모리도 늘 수 있습니다.

## 5. 취소와 타임아웃은 여러 층이다

상위 코루틴의 timeout은 기다리는 요청을 끝낼 수 있어도 실행 중인 OS 스레드의 동기 함수를 즉시 중단시키지 못합니다. 이미 S3에 보낸 쓰기 요청이 성공했을 수도 있습니다. ‘사용자가 취소했으니 외부 부작용도 없음’이라고 가정하지 않습니다.

SDK의 connect/read timeout, 재시도 횟수, 전체 요청 deadline, 동시성 한도를 함께 정합니다. botocore의 `total_max_attempts=1`은 최초 시도를 포함해 총 한 번이라는 뜻으로, 재시도 횟수를 세는 다른 옵션과 혼동하지 않습니다. 짧은 read timeout도 모든 단계의 총 경과 시간을 강제 제한하는 만능 설정은 아닙니다.

| 위험 | 관찰·대응 |
| --- | --- |
| 루프 막힘 | 호출 위치 추적, 루프 lag·동시 요청 지연 |
| 스레드 포화 | 실행/대기 수·작업 점유 시간, 입력 제한 |
| 연결 재사용 실패 | 본문 소비·close·풀 정책·재연결 확인 |
| 취소 후 잔여 작업 | SDK timeout·작업 수명·쓰기 결과 조회 |
| 큰 객체 메모리 | 전체 읽기 대신 제한된 스트리밍·배치 검토 |

## 적용 과제

위 코드에서 `.get_object()`만 오프로딩하고 `.read()`는 async 경로에 남겨둔 변형을 그려 봅니다. 여전히 루프가 막힐 수 있는 구간을 찾으세요. 그런 다음 객체 크기가 1KB에서 1GB로 바뀌면 필요한 설계가 무엇인지 적습니다. 이 조각 자체를 실행한 S3 결과로 취급하지 않습니다. 실제 S3 호환 환경 비교는 4-4에서 다룹니다.

## 퀴즈

Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 권장 통과 8점.

### Q1
`await boto3_client.get_object(...)`로 boto3를 비동기 SDK로 만들 수 있나요?

### Q2
본문 스트림을 읽는 작업도 블로킹 범위에 포함될 수 있나요?

### Q3
boto3 client의 일반적인 thread-safe 설명을 Session·Resource·다른 프로세스에 그대로 적용하면 안 되는 이유를 적으세요.

### Q4
상위 코루틴이 취소되었습니다. 이미 시작된 스레드의 S3 업로드도 반드시 중단됐나요? 필요한 확인을 쓰세요.

### Q5
큰 S3 객체를 반환하는 API를 설계하세요. 오프로딩 범위, 메모리·스트림 수명, 동시성, timeout·취소, 검증 항목을 포함합니다.

## 출처

2026-10-01 확인.

- [boto3 client 공식 가이드 원문](https://github.com/boto/boto3/blob/develop/docs/source/guide/clients.rst): `Multithreading or multiprocessing with clients`와 caveats.
- [botocore Config 원문](https://github.com/boto/botocore/blob/develop/botocore/config.py): connect/read timeout, retries, max_pool_connections.
- [Python asyncio task 3.12](https://github.com/python/cpython/blob/3.12/Doc/library/asyncio-task.rst): to_thread와 취소.
- [Starlette threadpool](https://github.com/Kludex/starlette/blob/main/docs/threadpool.md): AnyIO 실행과 제한.
