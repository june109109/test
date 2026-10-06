# 7-3. 구간별 타임아웃 예산

[목차](../README.md) · [정답·해설](03-timeout-budget-answers.md)

예상 55분. 목표: 전체 deadline과 connect/read/pool/idle timeout을 구분하고, 실패 응답을 돌려줄 여유를 계산합니다.

## 1. timeout=5가 5초 안에 끝난다는 뜻일까

httpx는 connect·read·write·pool timeout을 구분합니다. read timeout은 보통 다음 데이터 청크를 기다리는 시간이며 전체 응답 다운로드 시간과 다릅니다. boto3의 connect/read timeout도 전체 업무 deadline이 아닙니다. retry가 있으면 각 시도와 backoff가 합쳐집니다.

| 구간 | 대표 제한 | 무엇을 측정하는가 |
| --- | --- | --- |
| HTTP client | connect/read/write/pool | 연결·청크 전송/수신·풀 대기 |
| boto3 | connect_timeout/read_timeout + retry | SDK 시도별 네트워크와 재시도 |
| DB | pool wait/statement/lock timeout | 연결 대여·SQL 문장·락 획득 |
| 애플리케이션 | 요청 deadline | 전체 업무에 사용할 시간 |
| Uvicorn | keep-alive timeout | 요청 사이 유휴 연결; handler 실행 제한 아님 |
| LB/proxy | idle/request 등 제품별 | 연결 유휴 또는 요청 범위; 이름만으로 추정 금지 |

주기적으로 작은 청크가 도착하면 read/idle timeout을 넘기지 않고 전체 요청이 오래 지속될 수 있습니다. 대용량 다운로드와 일반 JSON API의 시간 예산이 다를 수 있습니다.

## 2. 안쪽에 먼저 실패할 기회를 준다

일반적인 짧은 API에서는 바깥 클라이언트의 deadline보다 안쪽 업무 deadline을 짧게 두어 오류 변환·rollback·응답 전송 여유를 확보합니다. 단, 모든 숫자를 기계적으로 ‘클라이언트 > LB > 서버 > DB’로 정렬하는 것이 정답은 아닙니다. idle 제한과 전체 deadline은 의미가 다릅니다.

설명용 예산: 사용자 전체 3초, 앱 업무 2.4초, 정리/전송 여유 0.6초. 앱은 인증 0.1초, DB 0.3초, 외부 호출 최대 1.4초, 변환 0.2초, 남은 여유 0.4초를 배분할 수 있습니다. 이 숫자는 측정 결과가 아닌 설계 초안입니다.

외부 호출의 1.4초 안에 pool wait·연결·읽기·retry·backoff를 모두 넣어야 합니다. 두 번의 시도 각각 read_timeout=1.4초이면 전체 1.4초 예산을 지키지 못합니다.

## 3. 남은 시간으로 하위 예산을 줄인다

deadline을 시작 시각+허용시간으로 잡고 각 단계에서 `remaining=deadline-now`를 계산합니다. 같은 프로세스의 경과 시간은 monotonic clock을 사용합니다. 다른 머신에 monotonic 절대값을 그대로 보내면 기준 시계가 달라 사용할 수 없습니다. 분산 전파는 프로토콜이 정한 deadline/remaining-time과 clock skew 처리를 따릅니다.

이미 남은 시간이 거의 없으면 새 retry를 시작하지 않습니다. 병렬 호출은 단순 합이 아니라 가장 오래 걸리는 경로가 중요하지만, 공유 연결 풀·CPU 경쟁으로 서로 지연시킬 수 있습니다.

## 4. 예산이 있어도 작업이 끝나지 않을 수 있다

`asyncio.timeout`은 취소를 통해 기다림을 제한하는 도구입니다. 루프를 동기 코드로 막으면 timeout callback도 제때 실행되지 못합니다. 스레드로 넘긴 블로킹 호출은 await가 취소되어도 계속 실행할 수 있습니다. 하위 라이브러리 자체 timeout·취소 지원·실행 중 작업 수를 함께 관리합니다.

클라이언트 연결이 끊겼다고 DB/외부 결제가 실행되지 않았다고 단정하지 마세요. 요청 종료와 부작용의 성공 여부는 다른 관찰입니다.

## 5. 적용 과제

요청 3초 한도에 DB 조회와 결제 API 두 단계가 있습니다. DB가 0.8초 사용했다면 결제 시도·재시도·정리 예산을 다시 계산하세요. SDK가 전체 timeout을 제공하지 않을 때 app deadline과 어떤 한계가 남는지 적습니다.

### Python 트랙 보강: 설정 단위가 보이는 예

```python
# HTTPX 설정 예시. 이 값들 자체가 총 요청 1초 한도는 아님.
timeout = httpx.Timeout(connect=0.2, read=0.8, write=0.5, pool=0.1)
# boto3 설정 예시. initial attempt를 포함해 최대2회 시도.
config = Config(connect_timeout=0.2, read_timeout=0.8,
                retries={"total_max_attempts": 2, "mode": "standard"})
```

설명용 조각이며 import·client 생성·대상 호출은 생략했습니다. 바깥 `asyncio.timeout`으로 총 기다림을 제한하더라도 스레드로 넘긴 boto3를 즉시 죽이지 못합니다. 외부 호출·backoff·풀 대기·rollback·응답 시간을 모두 예산에 넣습니다. Uvicorn의 keep-alive, LB idle timeout은 이 전체 업무 deadline과 다른 설정입니다. 숫자를 일렬로 크게/작게 배치하기 전에 무엇의 시간을 재는지 써 보세요.

## 퀴즈

### Q1

Uvicorn keep-alive timeout은 핸들러의 최대 실행 시간인가?

### Q2

read timeout 1초이면 전체 응답을 반드시 1초 안에 받는가?

### Q3

전체 deadline 안에 retry를 포함해야 하는 이유는?

### Q4

다른 머신에 monotonic clock 절대값을 그대로 보내면 안 되는 이유는?

### Q5

3초 요청의 DB·결제·재시도·정리 예산을 설정하고 각 설정의 의미를 구분하라.

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/) — 확장 읽기.
- [asyncio timeout](https://docs.python.org/3/library/asyncio-task.html#timeouts) — 취소 기반 시간 제한.
- boto3/DB 설정은 4-6·5-8의 확인한 구현 범위를 함께 읽으세요.

확인일: 2026-10-01. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
