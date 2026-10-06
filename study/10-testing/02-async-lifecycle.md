# 10-2. 비동기 테스트와 수명

[목차](../README.md) · [정답·해설](02-async-lifecycle-answers.md)

예상 55분. 목표: coroutine 실행, event loop, 앱 lifespan, client 수명을 맞춥니다.

## 1. 함수만 호출하면 실행된 것이 아니다

async 함수 호출은 coroutine 객체를 만들며 await 또는 적절한 실행기가 필요합니다. pytest-asyncio나 AnyIO plugin은 테스트에서 비동기 실행 환경을 제공합니다. 두 plugin의 자동 모드·marker를 무분별하게 섞으면 누가 실행을 담당하는지 모호해질 수 있습니다.

예제는 pytest-asyncio 0.25.3의 strict 모드와 명시적 `@pytest.mark.asyncio`, `@pytest_asyncio.fixture`를 사용합니다. 설정 파일은 fixture loop scope를 function으로 정합니다.

## 2. ASGITransport와 lifespan

httpx ASGITransport는 앱을 프로세스 내부에서 호출하므로 실제 TCP/TLS/Uvicorn을 통과하지 않습니다. 앱의 lifespan을 자동으로 시작한다고 가정하면 DB client 등이 준비되지 않을 수 있습니다.

```python
@pytest_asyncio.fixture
async def client():
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url='http://study.invalid',
        ) as client:
            yield client
```

[실제 fixture](../labs/testing_demo/conftest.py)는 앱 준비→client 사용→client 종료→앱 종료 순서를 보장합니다. 이 작은 예제는 FastAPI router의 lifespan context를 직접 사용합니다. 복잡한 ASGI 앱에서는 수명 관리 도구의 지원 범위도 확인하세요.

## 3. loop와 fixture scope

한 event loop에서 만든 비동기 client/pool을 다른 loop의 테스트에 재사용하면 ‘다른 loop에 연결’ 오류나 종료 문제가 생길 수 있습니다. 준비 비용 때문에 session scope를 쓰고 싶다면 리소스와 실행 loop 수명을 같이 맞춰야 합니다.

테스트 종료 후 백그라운드 task·스레드·서버가 남지 않도록 정리합니다. sleep을 넣어 타이밍을 맞추기보다 Event·조건·완료 신호로 필요한 상태를 기다립니다. 모든 대기에는 실패할 상한을 두어 suite 전체가 멈추지 않게 합니다.

## 4. 실제 검증 범위

예제 API는 lifespan에서 ready를 설정하고 `/quote`가 이를 확인합니다. 정상 요청 한 개와 입력 검증 오류 세 개가 API 테스트에 포함됩니다. 전체 21개 중 API 경로 4개입니다. shutdown의 모든 실패·실제 서버 disconnect·TCP 동작을 검증한 것은 아닙니다.

## 5. 적용 과제

DB pool을 lifespan에서 만드는 API를 테스트한다고 가정하세요. 함수별 트랜잭션 rollback, loop scope, 시작 실패, client 종료 뒤 pool 종료 순서를 그립니다.

보강: pytest-asyncio와 분리해 AnyIO marker/backend를 설정하는 실제 예제는 [10-7](07-python-toolkit.md)에 있습니다.

## 퀴즈

### Q1

async 함수를 호출만 하면 본문이 끝까지 실행되는가?

### Q2

ASGITransport가 항상 앱 lifespan도 자동 수행하는가?

### Q3

client와 앱 lifespan의 시작·종료 순서를 설명하라.

### Q4

session fixture의 async pool과 function loop가 충돌할 수 있는 이유는?

### Q5

비동기 DB API의 수명·격리·종료 검증 계획을 제안하라.

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- [pytest-asyncio concepts](https://pytest-asyncio.readthedocs.io/en/stable/concepts.html) — 후속 읽기.
- [실제 API 테스트](../labs/testing_demo/test_api.py), [실제 앱](../labs/testing_demo/quote_api.py).

확인일: 2026-10-02. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
