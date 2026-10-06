# 4-6. 스레드풀·HTTP 풀·비동기 SDK

[목차](../README.md) · [정답·해설](06-pools-answers.md)

예상 55분. 목표: 풀마다 제한하는 자원을 구분하고, boto3의 풀 설정을 동시성 제한으로 오해하지 않으며, SDK 교체 비용을 비교합니다.

## 1. ‘풀 크기’라는 이름은 같지만 대상은 다르다

| 자원·설정 | 주로 관리하는 대상 | 같은 숫자로 취급하면 안 되는 것 |
| --- | --- | --- |
| AnyIO thread limiter | 해당 오프로딩의 동시 실행 토큰 | 프로세스 전체 스레드·asyncio executor |
| asyncio 기본 executor | asyncio의 스레드 오프로딩 실행 | Starlette가 공유하는 AnyIO 한도 |
| HTTP 연결 풀 | 목적지 연결의 생성·재사용·보관 | 항상 요청 동시성 hard limit이라는 가정 |
| DB 풀 | DB 세션·연결 | HTTP 스트림·CPU 계산 용량 |
| 앱 semaphore·큐 | 앱이 정한 작업의 입장·대기 | 물리적으로 실행 중인 모든 작업의 강제 중단 |

각 구현에는 대기·overflow·timeout·반환의 규칙이 있습니다. 이름만 보고 곱셈하지 말고 무엇을 제한하는지 먼저 확인합니다. HTTP/2·3는 하나의 연결에 여러 스트림을 실을 수 있어 연결 수와 요청 수가 더욱 달라집니다.

## 2. boto3 max_pool_connections의 실제 범위

botocore Config는 이 값을 ‘풀에 보관할 최대 연결 수’로 설명합니다. 이 자료에서 실행한 **botocore 1.35.99 + urllib3 2.8.0**의 코드를 직접 확인했습니다.

```text
botocore URLLib3Session._get_pool_manager_kwargs:
    maxsize = self._max_pool_connections
    block 옵션은 지정하지 않음

urllib3 HTTPConnectionPool.__init__:
    maxsize=1, block=False, ...  # 생성자 기본값
```

이 경로에서는 풀이 비어 있고 block=False일 때 추가 연결을 만들 수 있습니다. 돌려줄 때 보관 한도를 넘는 연결은 재사용되지 않고 닫히는 방식일 수 있습니다. 따라서 **max_pool_connections=10이면 11번째 요청은 반드시 획득 대기한다**는 설명은 이 구현에 맞지 않습니다.

이 값이 무의미한 것은 아닙니다. 실제 병행 수에 비해 보관 한도가 작으면 재사용 효율이 나빠지고 ‘pool full’에 따른 연결 폐기가 늘 수 있습니다. 그것을 DB 풀과 같은 의미의 ‘풀 대기 지표’로 곧바로 해석하지 마세요. 버전·HTTP 경로·프록시 사용·대상별 pool을 확인해야 합니다.

## 3. 동시성·요청률·연결 보관을 따로 설계

동시성 10은 ‘지금 진행 중인 작업 최대 10’, 요청률 10/s는 ‘시간당 유입 속도’, 보관 연결 10은 ‘재사용할 연결의 수’에 관련됩니다. 같은 단위가 아닙니다.

100ms 걸리는 작업을 동시성 10으로 포화 실행하면 단순 근사로 100요청/초가 될 수 있습니다. 외부 API가 20요청/초만 허용한다면 동시성 10만으로 그 계약을 지킬 수 없습니다. rate limiter·retry budget도 필요할 수 있습니다.

| 조정 | 기대 이익 | 감수할 비용 |
| --- | --- | --- |
| 실행 토큰 증가 | 더 많은 동기 대기 병행 | 메모리·스레드·하류 부하 |
| 연결 보관 증가 | 재사용 개선 | 유휴 연결·FD·서버 자원 |
| 작업 입장 제한 | 과부하를 앞단에서 제어 | 거절·큐·사용자 재시도 정책 |
| 비동기 SDK | 많은 대기를 스레드 없이 관리 가능 | 기능·버전·세션·취소·관측 방식 변경 |

## 4. 취소 때 한도가 풀리는 함정

`asyncio.to_thread` 작업을 semaphore 안에서 기다리다가 코루틴이 취소되면 semaphore는 해제되지만 실행 중인 스레드는 남을 수 있습니다. 새 요청이 들어오면 논리 한도와 실제 잔여 작업 수가 달라질 수 있습니다. 실제 실행 자원의 한도, 작업 완료 추적, SDK timeout을 함께 고려해야 합니다.

AnyIO의 `run_sync`는 취소를 기다리는 방식·abandon 옵션 등 의미가 asyncio와 다를 수 있습니다. 두 함수를 단순 별칭으로 취급하지 않습니다. 작업마다 중단 가능한 범위와 ‘클라이언트 응답 종료 후에도 계속되는가’를 확인하세요.

## 5. aioboto3를 평가하는 기준

aioboto3·aiobotocore는 boto3와 유사한 비동기 사용을 제공하는 후보입니다. 이 편에서는 해당 패키지를 설치·성능 검증하지 않았습니다. 후보를 평가할 때 다음을 확인합니다.

- 필요한 S3 작업·페이지네이터·업로드 방식의 API와 실제 비동기 경계.
- boto3/botocore와 맞는 버전 조합, 세션·client의 async context manager 수명.
- 본문 read·close와 취소·오류 시 연결 정리.
- 커넥션 제한·DNS·프록시·인증 갱신·관측 방식.
- 현재 서비스에서 바꾸는 코드·테스트·운영 비용.

동시 요청이 작고 기존 SDK가 안정적이면 오프로딩이 더 경제적일 수 있습니다. 수많은 긴 I/O 대기가 있고 async 생태계가 갖춰졌다면 비동기 전환을 검토할 수 있습니다. 같은 객체·오류·자원 조건에서 측정하세요.

## 적용 과제

인스턴스 2개×워커 3개×AnyIO 토큰 40인 서비스를 그립니다. boto3 보관 풀은 워커당 10, 외부 API 허용량은 200요청/초입니다. ‘240개 요청이 항상 즉시 성공한다’는 결론의 문제를 찾고 실행·보관·요청률·큐·재시도를 따로 표시하세요.

### Python 트랙 보강: aioboto3 전환의 코드 경계

다음은 설치·실행하지 않은 API 사용 형태 예시입니다. client는 워커 lifespan에서 만들고, 버전 호환을 고정한 별도 환경에서 검증해야 합니다.

```python
# session은 aioboto3.Session(), bucket/key는 신뢰한 업무 입력이라는 전제
async with session.client("s3") as client:
    response = await client.get_object(Bucket=bucket, Key=key)
    async with response["Body"] as stream:
        payload = await stream.read()
```

client 생성·요청·본문 read·본문 종료의 수명을 모두 옮겨야 합니다. `await client.get_object`만 바꾸고 본문 소비·예외 정리를 빠뜨리면 충분하지 않습니다. 요청마다 client를 새로 만들면 풀 재사용 이익도 줄 수 있습니다. 실제 API·StreamingBody 동작은 선택한 aioboto3/aiobotocore 버전에서 확인하세요.

기존 boto3+오프로딩, aioboto3를 비교할 때 같은 객체 크기·동시 요청·실제 read/close·warmup·에러 정책을 적용합니다. boto3의 `max_pool_connections`와 비동기 connector의 한도가 같다고 가정하지 않습니다. [4-4](04-localstack.md)의180회 읽기는 boto3 경로만 검증한 결과입니다.

## 퀴즈

Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 권장 통과 8점.

### Q1
이 편에서 확인한 botocore 설정에서 max_pool_connections=10은 요청 동시성의 강제 상한인가요?

### Q2
asyncio.to_thread와 Starlette의 동기 경로가 항상 같은 limiter를 사용하나요?

### Q3
동시성 제한과 요청률 제한의 차이를 숫자 예로 설명하세요.

### Q4
코루틴 취소로 semaphore가 해제돼도 실제 블로킹 작업 수가 줄지 않을 수 있는 이유를 쓰세요.

### Q5
스레드 대기·연결 재생성·외부 429가 함께 증가합니다. 설정을 전부 늘리기 전 확인할 지표와 조치 순서를 설명하세요.

## 출처·확인 범위

2026-10-01 공식 문서와 설치된 구현 확인.

- [botocore Config](https://github.com/boto/botocore/blob/1.35.99/botocore/config.py): max_pool_connections와 retry 설정.
- [botocore HTTPSession](https://github.com/boto/botocore/blob/1.35.99/botocore/httpsession.py): PoolManager 전달 인자. 본문은 설치된 같은 버전의 함수 소스로 확인했습니다.
- [urllib3 HTTPConnectionPool](https://github.com/urllib3/urllib3/blob/2.8.0/src/urllib3/connectionpool.py): maxsize·block. 설치된 생성자 signature도 확인했습니다.
- [Starlette threadpool](https://github.com/Kludex/starlette/blob/main/docs/threadpool.md): AnyIO 공유 토큰.
- [Python asyncio task](https://github.com/python/cpython/blob/3.12/Doc/library/asyncio-task.rst): to_thread·취소.
