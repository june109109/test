# 4-7. 프로세스 시작과 클라이언트 수명

[목차](../README.md) · [정답·해설](07-lifecycle-answers.md)

예상 55분. 목표: import·워커 시작·요청·종료의 수명을 구분하고, 프로세스별 자원 초기화와 정상 종료를 설계합니다.

## 1. 자원은 언제 생기고 언제 닫히나

모듈 최상위에서 네트워크 client를 만들면 import 시점에 자원이 생깁니다. 테스트·개발 reload·여러 워커·프로세스 생성 방식에서 의도하지 않은 횟수로 초기화되거나 상속될 수 있습니다. 기본값 정의와 프로세스별 런타임 자원 생성을 구분하면 수명을 이해하기 쉽습니다.

| 수명 | 예 | 주의점 |
| --- | --- | --- |
| 코드 import | 함수·클래스 정의, 상수 | 외부 부작용이 있으면 도구·워커에서 반복될 수 있음 |
| 워커 lifespan | SDK client·연결 풀·로컬 캐시 | 프로세스마다 생성·메모리·연결 예산 발생 |
| 요청 | 요청별 인증·트랜잭션·본문 스트림 | 완료·오류·취소 시 정리 |
| 앱 전체 외부 자원 | 공유 DB·Redis·배포된 스키마 | 워커 종료마다 외부 서비스 자체를 삭제하지 않음 |

연결 풀을 닫는 것과 데이터베이스를 삭제하는 것은 완전히 다른 작업입니다. 소유한 자원만 올바른 수명에서 정리합니다.

## 2. FastAPI lifespan

다음은 형태를 설명하는 조각입니다. `create_client`·`close_client`는 선택한 SDK의 동기/비동기 API에 맞게 구현해야 합니다.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app):
    client = create_client()  # 워커 시작: 실제 블로킹 초기화 비용도 검토
    app.state.client = client
    try:
        yield  # 요청을 처리하는 구간
    finally:
        close_client(client)

app = FastAPI(lifespan=lifespan)
```

구체적인 client를 모르는 이 조각은 단독 실행 프로그램이 아닙니다. 동기 초기화·종료가 오래 걸리면 시작·종료 예산과 오프로딩을 검토합니다. 초기화 실패 시 준비되지 않은 워커가 요청을 받지 않도록 해야 합니다.

[PID 실습 앱](../labs/pid_app.py)은 실제 lifespan에서 워커별 임의 식별자와 로컬 카운터를 만들고 시작·종료 기록을 남깁니다. 이것은 SDK 연결 정상 종료를 직접 시험한 것은 아니지만 수명 경계의 실행을 확인하는 작은 실험입니다.

## 3. spawn·fork·forkserver

| 방식 | 동작 개요 | 이득·비용 |
| --- | --- | --- |
| spawn | 새 인터프리터가 필요한 코드를 import | 불필요한 상속 감소, 초기화·직렬화·main guard 필요 |
| fork | 부모 프로세스 상태에서 자식 생성 | copy-on-write 활용 가능, 스레드·락·소켓 상속 위험 |
| forkserver | 서버 프로세스가 자식 생성을 중개 | 멀티스레드 부모의 직접 fork 위험 감소, 별도 서버·초기화 조건 |

플랫폼·Python 버전에 따라 가능한 방식과 기본값이 다릅니다. Python 3.14의 기본 변경을 3.12 Linux와 혼동하지 않습니다. Uvicorn의 자체 멀티프로세스 구현은 별도의 시작 정책을 가지며, 이 환경의 0.52.1 코드에서는 spawn을 사용함을 확인했습니다.

fork의 copy-on-write는 이후 변경이 자동 공유된다는 뜻이 아닙니다. 메모리 페이지가 처음에는 공유될 수 있어도 쓰기 이후 비용이 달라집니다. 이미 열린 boto3 client를 자식 여러 개에 넘기는 것은 공식 client 공유 조건에 맞지 않습니다.

## 4. 종료의 순서

1. 새 트래픽의 유입을 줄이거나 중단합니다.
2. 진행 중 요청·백그라운드 작업이 끝날 기한을 둡니다.
3. 요청별 스트림·트랜잭션·client 자원을 정리합니다.
4. 워커 lifespan 자원을 닫고 프로세스를 끝냅니다.
5. 강제 종료가 필요했다면 미완료 외부 작업·중복 재시도의 처리 계약을 확인합니다.

SIGTERM에 대한 정상 종료와 SIGKILL·호스트 장애는 다릅니다. finally가 어떤 상황에서도 실행된다고 보장할 수 없습니다. 데이터 정확성은 정상 종료에만 의존하지 말고 트랜잭션·멱등성·복구 가능한 작업 상태를 이용해야 합니다.

## 5. 설계 비용 비교

프로세스마다 client를 만들면 격리와 수명은 명확해지지만 워커를 늘릴수록 연결·캐시·메모리도 늘어납니다. 외부 공유 서비스를 이용하면 공통 상태를 유지하기 쉽지만 네트워크·장애·운영 비용이 듭니다. 로컬 캐시는 빠르지만 전체 일관성·재시작 복구를 별도로 다뤄야 합니다.

개발 reload와 운영 workers를 같은 구성으로 이해하지 않습니다. reload는 코드 변경 감지와 재시작을 위한 개발 기능이고, 여러 워커는 실행 프로세스를 늘리는 구성입니다. 설치 버전의 CLI에서 서로 함께 사용할 수 있는지 확인하세요.

## 적용 과제

S3 client·DB 풀·사용자 인증 정보·다운로드 Body·캐시·데이터 마이그레이션을 어느 수명에서 만들고 닫을지 표시하세요. 특히 모든 워커가 동시에 실행하면 안 되는 작업과 워커마다 반드시 만들어야 하는 자원을 구분합니다. 마이그레이션을 lifespan에 무조건 넣지 않습니다.

## 퀴즈

Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 권장 통과 8점.

### Q1
워커가 4개면 lifespan 초기화는 전체 앱에서 반드시 한 번만 실행되나요?

### Q2
SIGKILL에서도 finally가 반드시 실행되나요?

### Q3
부모에서 만든 boto3 client를 여러 자식 프로세스가 공유하는 설계의 문제와 수정 방향을 적으세요.

### Q4
DB 스키마 마이그레이션을 모든 워커 lifespan에서 실행할 때의 위험 두 가지를 적으세요.

### Q5
S3 읽기와 DB 갱신을 수행하는 API의 시작·요청·종료를 설계하세요. 자원 소유, 준비 실패, 제한된 종료 대기, 강제 종료 뒤 복구를 포함합니다.

## 출처

2026-10-01 확인.

- [FastAPI lifespan 문서](https://github.com/fastapi/fastapi/blob/master/docs/en/docs/advanced/events.md): 시작·yield·종료 수명.
- [Python 3.14 multiprocessing](https://github.com/python/cpython/blob/3.14/Doc/library/multiprocessing.rst): 시작 방법·버전별 기본값.
- [boto3 client 가이드](https://github.com/boto/boto3/blob/develop/docs/source/guide/clients.rst): 프로세스 간 공유 제한.
- Uvicorn 0.52.1 설치 소스 `uvicorn._subprocess.get_subprocess`: spawn.Process 사용을 직접 확인했습니다.
