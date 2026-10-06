# 7-1. 로컬 캐시와 공유 캐시

[목차](../README.md) · [정답·해설](01-local-shared-answers.md)

예상 50분. 목표: 캐시의 위치·범위·수명을 구분하고, 멀티프로세스에서 무효화가 전파되지 않는 이유를 설명합니다.

## 1. ‘메모리에 넣었다’는 누구의 메모리인가

`functools.lru_cache`는 해당 프로세스 안에서 함수 인자에 대응하는 결과를 보관합니다. 워커가 4개면 일반적으로 별도 캐시 4개입니다. 함수 호출이 생략되어 계산·I/O 비용을 줄이지만, 외부 데이터 변경을 자동으로 알아내지 않습니다.

```python
from functools import lru_cache

@lru_cache(maxsize=256)
def tax_rule(region, version):
    return load_rule(region, version)  # 설명용 외부 함수
```

인자는 hashable이어야 합니다. `maxsize`는 대체로 항목 수 제한이며 바이트 단위 메모리 제한이 아닙니다. TTL도 내장되어 있지 않습니다. 캐시된 mutable 값을 수정하면 뒤의 호출자가 바뀐 객체를 받는 문제도 있습니다.

## 2. 대안 비교

| 선택 | 장점 | 비용·주의 |
| --- | --- | --- |
| lru_cache | 단순하고 네트워크 비용 없음 | 프로세스별 복제, TTL 없음, 메모리 점유 |
| cachetools TTLCache 등 | 만료·축출 정책 선택 | 일반 객체의 thread safety·시간·크기 정책 확인 |
| Redis 공유 캐시 | 워커들이 같은 상태 조회, TTL·원자 연산 | 네트워크·직렬화·장애·운영 비용 |
| DB 직접 조회 | 캐시 불일치 경로 감소 | 반복 조회 비용·DB 부하 |
| L1 로컬 + L2 공유 | 빠른 근접 조회와 공유 계층 | 두 단계 무효화·메모리·관측 복잡도 |

`lru_cache`의 내부 자료구조가 스레드 사용에 안전하다는 것과 동일 miss를 한 번만 계산한다는 것은 다릅니다. 초기 계산이 끝나기 전에 여러 호출이 들어오면 함수가 여러 번 실행될 수 있습니다. single-flight는 별도 문제입니다.

`async def`에 동기 lru_cache를 그대로 붙이면 완료된 결과 대신 coroutine 객체를 캐시하여 재사용 문제가 생길 수 있습니다. 비동기 결과·실패·취소를 어떻게 다룰지 정의한 구현을 사용하세요.

## 3. 실제 두 프로세스 실험

[코드](../labs/cache_cancellation.py), [결과](../results/cache-cancellation-2026-10-01.json).

```bash
python3 study/labs/cache_cancellation.py --output /tmp/cache-new.json
```

표준 라이브러리만 사용하며 spawn 프로세스 두 개를 만들고 임시 파일을 공통 원본으로 읽습니다. Redis를 실행한 실험은 아닙니다.

| 단계 | 워커 A | 워커 B |
| --- | --- | --- |
| 원본 version-1, 첫 조회 | version-1 | version-1 |
| 원본 version-2로 변경, A만 cache_clear | version-2 | version-1 |
| B도 cache_clear 후 조회 | 이미 version-2 | version-2 |

2026-10-01 직접 확인했습니다. 원본 변경 후 자동 갱신이 없다는 사실과 무효화 범위가 프로세스별이라는 사실이 핵심입니다. 임시 파일·프로세스는 종료 시 정리합니다.

## 4. 캐시할 대상 고르기

배포 동안 변하지 않는 작은 설정·버전별 변환 결과는 로컬 캐시에 잘 맞을 수 있습니다. 여러 워커가 즉시 공유해야 하는 세션 폐기 정보나 재고의 유일한 사실을 로컬 캐시만으로 처리하면 안 됩니다.

TTL 30초라고 데이터가 정확히 30초만 오래되는 것도 항상 보장되지 않습니다. 원본 복제 지연·재생성 시간·stale 응답 정책·캐시 시간 측정 지점이 더해질 수 있습니다. 비즈니스가 허용하는 신선도를 먼저 정합니다.

## 5. 적용 과제

4워커의 국가별 정적 요금표와 사용자별 접근권한을 각각 캐시한다고 합시다. 키·버전·만료·권한 변경 전파·장애 시 원본 조회 여부를 설계하세요.

### Python 트랙 보강: TTLCache의 시간과 동시성

cachetools TTLCache는 `timer`를 주입할 수 있어 실제 sleep 없이 만료 직전·정확한 만료를 검사할 수 있습니다. 이번 보강의 [실행 테스트](../labs/python_track_tests/test_toolkit.py)는0초에 저장한 TTL10초 값을9.999초에는 읽고10초에는 miss인지 확인합니다.

TTL이 지난 값의 조회 차단과 물리 메모리에서 즉시 제거는 다른 문제입니다. 구현의 expire/변경 시 정리 정책도 확인하세요. TTLCache 객체는 thread-safe라고 가정하지 않습니다. 락으로 딕셔너리를 보호해도 동시 miss 계산을 하나로 묶는 single-flight는 별도입니다. 긴 I/O 동안 같은 락을 잡으면 모든 키의 조회를 직렬화할 수 있습니다. 사용자/테넌트·권한 버전을 키에 포함할 조건도 [7-2](02-invalidation.md)와 연결합니다.

## 퀴즈

### Q1

한 워커의 cache_clear는 다른 워커에도 자동 반영되는가?

### Q2

lru_cache(maxsize=100)는 메모리 100바이트 제한인가?

### Q3

lru_cache와 Redis의 주요 이익·비용을 비교하라.

### Q4

스레드 안전한 캐시에서도 같은 miss 계산이 중복될 수 있는 이유는?

### Q5

정적 요금표와 동적인 접근권한의 캐시 정책을 각각 설계하라.

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- [CPython functools 문서](https://docs.python.org/3/library/functools.html#functools.lru_cache) — lru_cache의 범위·동시 호출 특성.
- [cachetools 문서](https://cachetools.readthedocs.io/en/stable/) — 후속 읽기. Redis/cachetools 실물 비교는 수행하지 않았습니다.

확인일: 2026-10-01. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
